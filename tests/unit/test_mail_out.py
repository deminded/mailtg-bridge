from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import default
from mailtg_bridge.config import Settings
from mailtg_bridge.domain import *
from mailtg_bridge.mail_out import EmailComposer
from test_config import env

def test_mime_plain_html_and_exact_limit(tmp_path):
    e=env(tmp_path); e['EMAIL_SIZE_LIMIT_BYTES']='5000'; e['ATTACHMENT_THRESHOLD_BYTES']='1000'
    s=Settings.from_env(environ=e); c=EmailComposer(s)
    d=DialogRef('@chan',SourceType.CHANNEL,title='C',username='chan')
    b=DialogBatch(d,(TgMessage(1,d.dialog_id,datetime.now(timezone.utc),Sender('A'),'<unsafe>'),),1)
    drafts=c.compose_batch(b,{})
    assert len(drafts)==1 and len(drafts[0].raw)<=5000
    m=message_from_bytes(drafts[0].raw,policy=default)
    assert m.get_body(('plain',)) and '&lt;unsafe&gt;' in m.get_body(('html',)).get_content()

def test_oversize_splits_between_messages(tmp_path):
    e=env(tmp_path); e['EMAIL_SIZE_LIMIT_BYTES']='1800'; e['ATTACHMENT_THRESHOLD_BYTES']='1000'
    s=Settings.from_env(environ=e); c=EmailComposer(s); d=DialogRef('d',SourceType.DM,title='D')
    ms=tuple(TgMessage(i,'d',datetime.now(timezone.utc),text='x'*500) for i in range(1,4))
    drafts=c.compose_batch(DialogBatch(d,ms,3),{})
    assert len(drafts)>1 and all(len(x.raw)<=1800 for x in drafts)
