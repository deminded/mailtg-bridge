from __future__ import annotations
import hashlib, html, imaplib, logging, smtplib, ssl, time, uuid
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate
from pathlib import Path
from .algorithms import build_deeplink
from .config import SecurityMode, Settings
from .domain import DialogBatch, DownloadedMedia, MailDraft, SentMail, SourceType
from .errors import MailAuthError, MailSizeRejected, Transient

log=logging.getLogger(__name__)

def make_message_id(domain: str) -> str: return f"<{uuid.uuid4().hex}@{domain}>"

# dict-source-type.md fixes the wire tag per source type; reply-routing keys off the dialog
# named here, so the tag is contract not decoration.
_SOURCE_TAG={SourceType.DM:"dm",SourceType.CHANNEL:"ch",SourceType.GROUP:"gr",SourceType.TOPIC:"gr"}
_ENTITY_TAG={"bold":"b","italic":"i","code":"code","pre":"pre"}

def render_entities(text: str, entities) -> str:
    # Telegram carries formatting as offset/length spans, not markup; without this a bold/
    # italic/code/pre/text-link message shows up as flat plain text in the email.
    if not entities: return html.escape(text)
    starts: dict[int,list] = {}; ends: dict[int,list] = {}
    for e in entities:
        starts.setdefault(e.offset,[]).append(e); ends.setdefault(e.offset+e.length,[]).append(e)
    for lst in starts.values(): lst.sort(key=lambda e:-e.length)  # outer entity opens first when co-located
    def tag(e,opening):
        if e.kind=="texturl": return f'<a href="{html.escape(e.url or "")}">' if opening else "</a>"
        t=_ENTITY_TAG.get(e.kind)
        return (f"<{t}>" if opening else f"</{t}>") if t else ""
    out=[]; stack: list=[]; i=0
    for pos in sorted({0,len(text)}|set(starts)|set(ends)):
        if pos>i: out.append(html.escape(text[i:pos]))
        closing=[e for e in reversed(stack) if e.offset+e.length==pos]
        out.extend(tag(e,False) for e in closing)
        stack=[e for e in stack if e.offset+e.length!=pos]
        for e in starts.get(pos,()): out.append(tag(e,True)); stack.append(e)
        i=pos
    return "".join(out)

class EmailComposer:
    def __init__(self,settings: Settings): self.s=settings; self.domain=settings.b_address.split("@")[-1]
    def _render(self,batch: DialogBatch, media, omitted=frozenset()):
        plain=[]; blocks=[]; attachments=[]
        for m in batch.messages:
            link=build_deeplink(batch.dialog,m.msg_id); author=m.sender.display_name or m.sender.username or "Telegram"
            plain.append(f"{author} — {m.date.isoformat()}\n{m.text or '[media]'}"+(f"\n{link}" if link else ""))
            body=(render_entities(m.text,m.entities) if m.text else html.escape("[media]")).replace("\n","<br>")
            block=f"<article><b>{html.escape(author)}</b> <time>{html.escape(m.date.isoformat())}</time><p>{body}</p>"
            if link: block+=f'<a href="{html.escape(link)}">Open in Telegram</a>'
            for dm in media.get(m.msg_id,()):
                if not dm.available:
                    # download failed (MediaUnavailable) -> explicit marker, not a silently dropped message
                    marker=f"[media unavailable: {dm.ref.content_type}]"; block+=f"<p>{html.escape(marker)}</p>"; plain[-1]+="\n"+marker; continue
                key=str(dm.path)
                if key in omitted or (not dm.ref.content_type.startswith("image/") and dm.size>self.s.attachment_threshold_bytes):
                    marker=f"[omitted media: {dm.ref.content_type}, {dm.size} bytes]"; block+=f"<p>{html.escape(marker)}</p>"; plain[-1]+="\n"+marker; continue
                if dm.ref.content_type.startswith("image/"):
                    cid=hashlib.sha256(key.encode()).hexdigest()[:24]
                    block+=f'<img src="cid:{cid}" alt="inline image">'
                attachments.append(dm)
            blocks.append(block+"</article>")
        return "\n\n".join(plain),"<html><body>"+"".join(blocks)+"</body></html>",attachments
    def _message(self,batch,media,part,nparts,omitted=frozenset()):
        msg=EmailMessage(); mid=make_message_id(self.domain); msg["From"]=self.s.b_address; msg["To"]=self.s.u_address
        _name=batch.dialog.title or (f"@{batch.dialog.username}" if batch.dialog.username else batch.dialog.source_tag or batch.dialog.dialog_id)
        topic=f"/{batch.dialog.topic_id}" if batch.dialog.source_type is SourceType.TOPIC and batch.dialog.topic_id is not None else ""
        base=f"{_SOURCE_TAG[batch.dialog.source_type]}:{_name}{topic}"
        msg["Subject"]=base+(f" ({part}/{nparts})" if nparts>1 else ""); msg["Message-ID"]=mid; msg["Date"]=formatdate(localtime=False)
        plain,markup,attachments=self._render(batch,media,omitted); msg.set_content(plain or "Telegram update"); msg.add_alternative(markup,subtype="html")
        html_part=msg.get_payload()[-1]
        for dm in attachments:
            maintype,subtype=(dm.ref.content_type if "/" in dm.ref.content_type else "application/octet-stream").split("/",1)
            data=dm.path.read_bytes()
            if maintype=="image":
                cid=hashlib.sha256(str(dm.path).encode()).hexdigest()[:24]
                html_part.add_related(data,maintype=maintype,subtype=subtype,cid=f"<{cid}>",filename=dm.ref.filename)
            elif dm.size<=self.s.attachment_threshold_bytes: msg.add_attachment(data,maintype=maintype,subtype=subtype,filename=dm.ref.filename)
        return msg,mid
    def compose_batch(self,batch: DialogBatch,media):
        groups=[batch.messages]
        while True:
            drafts=[]; oversized=False
            for i,messages in enumerate(groups,1):
                sub=DialogBatch(batch.dialog,tuple(messages),batch.high_watermark); msg,mid=self._message(sub,media,i,len(groups))
                raw=msg.as_bytes(policy=SMTP)
                if len(raw)>self.s.email_size_limit_bytes and len(messages)>1:
                    n=len(messages)//2; groups[groups.index(messages):groups.index(messages)+1]=[messages[:n],messages[n:]]; oversized=True; break
                if len(raw)>self.s.email_size_limit_bytes:
                    paths=sorted((str(x.path) for x in media.get(messages[0].msg_id,())),key=lambda p:Path(p).stat().st_size,reverse=True)
                    msg,mid=self._message(sub,media,i,len(groups),frozenset(paths)); raw=msg.as_bytes(policy=SMTP)
                if len(raw)>self.s.email_size_limit_bytes: raise MailSizeRejected("message cannot fit configured MIME limit")
                drafts.append(MailDraft(mid,self.s.u_address,str(msg["Subject"]),raw,batch.dialog.dialog_id))
            if not oversized: return drafts

class SmtpMailer:
    def __init__(self,settings: Settings): self.s=settings
    def send(self,draft: MailDraft):
        ctx=ssl.create_default_context()
        try:
            if self.s.b_smtp_security is SecurityMode.SSL: smtp=smtplib.SMTP_SSL(self.s.b_smtp_host,self.s.b_smtp_port,context=ctx,timeout=120)
            else:
                smtp=smtplib.SMTP(self.s.b_smtp_host,self.s.b_smtp_port,timeout=120); smtp.ehlo(); smtp.starttls(context=ctx); smtp.ehlo()
            with smtp: smtp.login(self.s.b_username,self.s.b_password); smtp.sendmail(self.s.b_address,[draft.to],draft.raw)
        except smtplib.SMTPAuthenticationError as exc: raise MailAuthError("SMTP authentication failed") from exc
        except smtplib.SMTPDataError as exc:
            if exc.smtp_code in {552,554}: raise MailSizeRejected("SMTP rejected message size") from exc
            raise Transient("SMTP rejected message") from exc
        except (OSError,smtplib.SMTPException) as exc: raise Transient("SMTP delivery failed") from exc
        self._archive_sent(draft.raw)
        return SentMail(draft.message_id,draft.dialog_id or "",__import__('mailtg_bridge.domain',fromlist=['SourceType']).SourceType.DM,self.s.b_address)
    def _archive_sent(self,raw: bytes) -> None:
        # SMTP send leaves no server-side trace on many providers, so the user can't
        # verify what the bridge actually delivered. Mirror each sent message into B's
        # Sent folder. Best-effort: a failed archive must never fail the delivery.
        if not self.s.save_sent_copy: return
        ctx=ssl.create_default_context()
        try:
            if self.s.b_imap_security is SecurityMode.SSL: m=imaplib.IMAP4_SSL(self.s.b_imap_host,self.s.b_imap_port,ssl_context=ctx,timeout=120)
            else:
                m=imaplib.IMAP4(self.s.b_imap_host,self.s.b_imap_port,timeout=120); m.starttls(ssl_context=ctx)
            try:
                m.login(self.s.b_username,self.s.b_password); m.append(self.s.sent_folder,r"(\Seen)",imaplib.Time2Internaldate(time.time()),raw)
            finally:
                try: m.logout()
                except Exception: pass
        except Exception as exc: log.warning("sent-copy archive failed",extra={"operation":"archive","error_class":type(exc).__name__})
    def send_notice(self,subject,body):
        msg=EmailMessage(); mid=make_message_id(self.s.b_address.split('@')[-1]); msg['From']=self.s.b_address; msg['To']=self.s.u_address; msg['Subject']=subject; msg['Message-ID']=mid; msg.set_content(body)
        self.send(MailDraft(mid,self.s.u_address,subject,msg.as_bytes(policy=SMTP))); return mid
