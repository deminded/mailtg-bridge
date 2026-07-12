from __future__ import annotations
import html, mimetypes, smtplib, ssl, uuid
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import formatdate
from pathlib import Path
from .algorithms import build_deeplink
from .config import SecurityMode, Settings
from .domain import DialogBatch, DownloadedMedia, MailDraft, SentMail
from .errors import MailAuthError, MailSizeRejected, Transient

def make_message_id(domain: str) -> str: return f"<{uuid.uuid4().hex}@{domain}>"

class EmailComposer:
    def __init__(self,settings: Settings): self.s=settings; self.domain=settings.b_address.split("@")[-1]
    def _render(self,batch: DialogBatch, media, omitted=frozenset()):
        plain=[]; blocks=[]; attachments=[]
        for m in batch.messages:
            link=build_deeplink(batch.dialog,m.msg_id); author=m.sender.display_name or m.sender.username or "Telegram"
            plain.append(f"{author} — {m.date.isoformat()}\n{m.text or '[media]'}"+(f"\n{link}" if link else ""))
            body=html.escape(m.text or "[media]").replace("\n","<br>")
            block=f"<article><b>{html.escape(author)}</b> <time>{html.escape(m.date.isoformat())}</time><p>{body}</p>"
            if link: block+=f'<a href="{html.escape(link)}">Open in Telegram</a>'
            for dm in media.get(m.msg_id,()):
                key=str(dm.path)
                if key in omitted: block+=f"<p>[omitted media: {html.escape(dm.ref.content_type)}, {dm.size} bytes]</p>"; continue
                attachments.append(dm)
            blocks.append(block+"</article>")
        return "\n\n".join(plain),"<html><body>"+"".join(blocks)+"</body></html>",attachments
    def _message(self,batch,media,part,nparts,omitted=frozenset()):
        msg=EmailMessage(); mid=make_message_id(self.domain); msg["From"]=self.s.b_address; msg["To"]=self.s.u_address
        base=f"Telegram: {batch.dialog.source_tag or batch.dialog.title or batch.dialog.dialog_id}"
        msg["Subject"]=base+(f" ({part}/{nparts})" if nparts>1 else ""); msg["Message-ID"]=mid; msg["Date"]=formatdate(localtime=False)
        plain,markup,attachments=self._render(batch,media,omitted); msg.set_content(plain or "Telegram update"); msg.add_alternative(markup,subtype="html")
        html_part=msg.get_payload()[-1]
        for dm in attachments:
            maintype,subtype=(dm.ref.content_type if "/" in dm.ref.content_type else "application/octet-stream").split("/",1)
            data=dm.path.read_bytes()
            if maintype=="image": html_part.add_related(data,maintype=maintype,subtype=subtype,cid=f"<{uuid.uuid4().hex}>",filename=dm.ref.filename)
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
        return SentMail(draft.message_id,draft.dialog_id or "",__import__('mailtg_bridge.domain',fromlist=['SourceType']).SourceType.DM,self.s.b_address)
    def send_notice(self,subject,body):
        msg=EmailMessage(); mid=make_message_id(self.s.b_address.split('@')[-1]); msg['From']=self.s.b_address; msg['To']=self.s.u_address; msg['Subject']=subject; msg['Message-ID']=mid; msg.set_content(body)
        self.send(MailDraft(mid,self.s.u_address,subject,msg.as_bytes(policy=SMTP))); return mid
