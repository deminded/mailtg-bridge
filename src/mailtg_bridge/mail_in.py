from __future__ import annotations
import email, imaplib, re, ssl
from email.header import decode_header
from email.policy import default
from email.utils import getaddresses, parseaddr
from html.parser import HTMLParser
from .config import SecurityMode, Settings
from .domain import InboundMail
from .errors import MailAuthError, Transient

def decode_header_value(value: str | None) -> str:
    out=[]
    for chunk,charset in decode_header(value or ""):
        out.append(chunk.decode(charset or "utf-8","replace") if isinstance(chunk,bytes) else chunk)
    return " ".join("".join(out).split())

def message_ids(value: str | None) -> tuple[str,...]:
    return tuple(re.findall(r"<[^<>\s]+>"," ".join((value or "").split())))

_BLOCK={"p","div","br","li","tr","h1","h2","h3","h4","h5","h6","blockquote","table","ul","ol","pre"}
_QUOTE_TAGS={"blockquote","cite"}
class _Text(HTMLParser):
    # Preserve block-level line breaks (so quoted tails stay on their own lines,
    # detectable by strip_quoted_tail) and skip quoted originals. Mail clients wrap the
    # citation in <blockquote> or a gmail_quote/cite container; we skip only that subtree
    # — tracked by the nesting depth of the tag that opened it — so the user's own text
    # after or between quotes (an inline reply, a trailing P.S.) is still captured.
    def __init__(self): super().__init__(); self.parts=[]; self._skip=0; self._skip_tag=None
    def _is_quote(self,tag,cls):
        return tag in _QUOTE_TAGS or "gmail_quote" in cls or "moz-cite" in cls or "quoted" in cls
    def handle_starttag(self,tag,attrs):
        if self._skip:
            if tag==self._skip_tag: self._skip+=1
            return
        cls=" ".join(v for k,v in attrs if k=="class" and v).lower()
        if self._is_quote(tag,cls): self._skip=1; self._skip_tag=tag; return
        if tag in _BLOCK: self.parts.append("\n")
    def handle_endtag(self,tag):
        if self._skip and tag==self._skip_tag:
            self._skip-=1
            if self._skip==0: self._skip_tag=None
    def handle_startendtag(self,tag,attrs):
        if not self._skip and tag=="br": self.parts.append("\n")
    def handle_data(self,data):
        if not self._skip: self.parts.append(data)
def html_to_text(value: str) -> str:
    p=_Text(); p.feed(value); p.close()
    lines=[" ".join(seg.split()) for seg in "".join(p.parts).split("\n")]
    out: list[str]=[]
    for ln in lines:  # collapse runs of blank lines, keep single separators
        if ln or (out and out[-1]): out.append(ln)
    return "\n".join(out).strip()

# A reply's quoted tail is delimited by an attribution line ("... wrote:", the
# Russian "... писал(а):", a forwarded-message banner) or a citation rule. Clients
# vary by locale, so match a family of markers, not just Gmail's English one — the
# live test leaked a Russian-client tail because only "On ... wrote:" was covered.
_QUOTE_TAIL=re.compile(
    r"""^\s*(?:
        >.*                                              # a quoted line
      | --\s*                                            # signature delimiter ("-- " on its own line)
      | -{2,}\s*(?:Original\ Message|Forwarded\ message|Пересыла\w*|Исходное\ сообщение)\s*-{2,}\s*
      | _{5,}\s* | -{5,}\s*                              # citation rule
      | (?:Кому|От|Отправлено|Дата|Копия|To|From|Sent|Cc|Date|Reply-To)\s*:.*  # quoted-header block (Yandex/Outlook)
      | .*\bwrote:\s*                                    # English "... wrote:"
      | .*\b(?:написал|писал)(?:\([аи]\)|[аи])?\s*:\s*   # Russian "... писал(а)/писала/писали:"
      | .*<[^<>\s]+@[^<>\s]+>\s*:\s*                     # attribution ending with "<email>:" (Yandex/Outlook)
    )$""",
    re.I | re.X,
)

def strip_quoted_tail(text: str) -> str:
    lines=[]
    for line in text.splitlines():
        if _QUOTE_TAIL.match(line): break
        lines.append(line)
    return "\n".join(lines).strip()

def extract_reply_text(msg: email.message.EmailMessage) -> str:
    text=""
    part=msg.get_body(preferencelist=("plain",)) if msg.is_multipart() else msg
    if part and part.get_content_type()=="text/plain": text=part.get_content()
    elif (part:=msg.get_body(preferencelist=("html",))): text=html_to_text(part.get_content())
    return strip_quoted_tail(text)

def is_auto_or_loop(msg: email.message.EmailMessage, our_addr: str) -> bool:
    sender=parseaddr(msg.get("From", ""))[1].lower()
    return sender==our_addr.lower() or (msg.get("Auto-Submitted", "no").lower() not in {"","no"}) or bool(msg.get("List-Id")) or msg.get("Precedence","").lower() in {"bulk","junk","list"}

def parse_inbound(raw: bytes, mail_ref: str) -> InboundMail:
    msg=email.message_from_bytes(raw,policy=default)
    recipient_headers=[str(v) for k in ("To","Delivered-To","X-Original-To") if (v:=msg.get(k))]
    recipients=tuple(a.lower() for _,a in getaddresses(recipient_headers) if a)
    attachments=any(p.get_content_disposition()=="attachment" for p in msg.walk())
    return InboundMail(mail_ref,parseaddr(msg.get("From",""))[1].lower(),recipients,decode_header_value(msg.get("Subject")),
        extract_reply_text(msg)," ".join((msg.get("Message-ID") or "").split()),message_ids(msg.get("In-Reply-To")),
        message_ids(msg.get("References")),is_auto_or_loop(msg, parseaddr(msg.get("To", ""))[1]),attachments)

class MailClassifier:
    def __init__(self,user_address: str,bridge_address: str): self.user=user_address.lower(); self.bridge=bridge_address.lower()
    def trusted(self,mail: InboundMail) -> bool:
        return not mail.auto_or_loop and mail.from_addr==self.user and self.bridge in mail.recipients
    def parent_ids(self,mail: InboundMail) -> tuple[str,...]: return mail.in_reply_to+tuple(reversed(mail.references))

class ImapMailbox:
    def __init__(self, settings: Settings): self.s=settings
    def _connect(self):
        ctx=ssl.create_default_context()
        try:
            if self.s.b_imap_security is SecurityMode.SSL: m=imaplib.IMAP4_SSL(self.s.b_imap_host,self.s.b_imap_port,ssl_context=ctx,timeout=120)
            else:
                m=imaplib.IMAP4(self.s.b_imap_host,self.s.b_imap_port,timeout=120); m.starttls(ssl_context=ctx)
            m.login(self.s.b_username,self.s.b_password); m.select("INBOX",readonly=True); return m
        except imaplib.IMAP4.error as exc: raise MailAuthError("IMAP authentication failed") from exc
        except OSError as exc: raise Transient("IMAP connection failed") from exc
    def poll(self):
        m=self._connect(); results=[]
        try:
            typ,data=m.response("UIDVALIDITY"); uidv=(data or [b"unknown"])[0].decode()
            typ,data=m.uid("search",None,"ALL")
            for uid in (data[0].split() if typ=="OK" and data and data[0] else []):
                typ,raw=m.uid("fetch",uid,"(BODY.PEEK[])")
                if typ!="OK" or not raw or not isinstance(raw[0],tuple): raise Transient("IMAP fetch failed")
                results.append(parse_inbound(raw[0][1],f"INBOX:{uidv}:{uid.decode()}"))
            return results
        finally:
            try: m.logout()
            except Exception: pass
