from datetime import datetime, timezone
from email import message_from_bytes
from email.policy import default
from mailtg_bridge.config import Settings
from mailtg_bridge.domain import *
from mailtg_bridge.mail_out import EmailComposer
from tests.helpers import settings_env as env

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

def test_inline_image_has_referenced_cid(tmp_path):
    e=env(tmp_path); e['EMAIL_SIZE_LIMIT_BYTES']='10000'; e['ATTACHMENT_THRESHOLD_BYTES']='1000'
    s=Settings.from_env(environ=e); c=EmailComposer(s); d=DialogRef('d',SourceType.DM,title='D')
    m=TgMessage(1,'d',datetime.now(timezone.utc),media=(MediaRef('1','x.png','image/png',8),)); p=tmp_path/'x.png'; p.write_bytes(b'\x89PNGdata')
    raw=c.compose_batch(DialogBatch(d,(m,),1),{1:[DownloadedMedia(m.media[0],p,8)]})[0].raw
    parsed=message_from_bytes(raw,policy=default); markup=parsed.get_body(('html',)).get_content()
    cids=[x['Content-ID'].strip('<>') for x in parsed.walk() if x.get('Content-ID')]
    assert cids and f'cid:{cids[0]}' in markup

def test_subject_shows_sender_name_not_numeric_id(tmp_path):
    # Regression: production DialogRef has source_tag=<numeric id> (from _dialog),
    # which previously shadowed title -> subject was "Telegram: <id>" (spam-prone, hides author).
    # Fixture MUST mirror production (source_tag populated), else the bug hides (the original test gap).
    e=env(tmp_path); s=Settings.from_env(environ=e); c=EmailComposer(s)
    d=DialogRef('7209976320',SourceType.DM,title='Arête',username='arete_limen',source_tag='7209976320')
    draft=c.compose_batch(DialogBatch(d,(TgMessage(1,d.dialog_id,datetime.now(timezone.utc),Sender('Arête'),'hi'),),1),{})[0]
    assert 'Arête' in draft.subject or 'arete_limen' in draft.subject, f"subject must show sender name: {draft.subject!r}"
    assert '7209976320' not in draft.subject, f"subject must not be the bare numeric id: {draft.subject!r}"

def test_body_shows_author_and_deeplink(tmp_path):
    # TKT-10 presentation fidelity operationalised: HTML body must carry author + deep-link.
    e=env(tmp_path); s=Settings.from_env(environ=e); c=EmailComposer(s)
    d=DialogRef('-1001234567890',SourceType.CHANNEL,title='Chan',username='mychan',source_tag='-1001234567890')
    m=TgMessage(42,d.dialog_id,datetime.now(timezone.utc),Sender('Alice','alice',5),'hello')
    raw=c.compose_batch(DialogBatch(d,(m,),42),{})[0].raw
    html=message_from_bytes(raw,policy=default).get_body(('html',)).get_content()
    assert 'Alice' in html, "author name must be shown in body (TKT-10)"
    assert 'https://t.me/mychan/42' in html, "deep-link to the message must be present"
