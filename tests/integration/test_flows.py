from datetime import datetime, timezone
import asyncio
from email.message import EmailMessage
import pytest
from mailtg_bridge.config import Settings
from mailtg_bridge.domain import *
from mailtg_bridge.mail_in import parse_inbound
from mailtg_bridge.orchestrator import BridgeService
from mailtg_bridge.state import SQLiteStore
from tests.helpers import settings_env as env

class Tg:
    def __init__(self,d,m): self.d=d; self.m=m; self.posts=[]; self.calls=0
    async def list_tracked_dialogs(self): self.calls+=1; return [self.d]
    async def fetch_since(self,*a): return self.m
    async def download_media(self,m): return []
    async def post_as_user(self,d,t): self.posts.append((d,t)); return 99
class In:
    def __init__(self,m=()): self.m=m
    def poll(self): return self.m
class Out:
    def __init__(self): self.sent=[]; self.notices=[]
    def compose_batch(self,b,media): return [MailDraft('<new@x>','u@x','s',b'x',b.dialog.dialog_id)]
    def send(self,d): self.sent.append(d); return SentMail(d.message_id,d.dialog_id,SourceType.DM,'b@x')
    def send_notice(self,s,b): self.notices.append((s,b)); return '<n@x>'

def settings(tmp_path,history=True):
    e=env(tmp_path); e['BOOTSTRAP_MODE']='history' if history else 'tail'; e['WHITELIST_JSON']='["-1001"]'; return Settings.from_env(environ=e)

def test_inbound_gate_delivery_cursor_and_echo(tmp_path):
    s=settings(tmp_path); d=DialogRef('-1001',SourceType.CHANNEL,whitelisted=True)
    msgs=[TgMessage(2,d.dialog_id,datetime.now(timezone.utc),text='ok'),TgMessage(3,d.dialog_id,datetime.now(timezone.utc),text='echo')]
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); st.commit_reply('old',d.dialog_id,3); out=Out(); svc=BridgeService(s,st,Tg(d,msgs),In(),out)
        asyncio.run(svc.run_inbound_cycle()); assert len(out.sent)==1 and st.get_cursor(d).last_id==3

def test_reply_action_then_consume_and_command(tmp_path):
    s=settings(tmp_path); d=DialogRef('-1001',SourceType.CHANNEL)
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); st.get_cursor(d); st.commit_delivery(d,[SentMail('<root@x>',d.dialog_id,d.source_type)],1)
        def mail(ref,subject,body):
            m=EmailMessage(); m['From']=s.u_address; m['To']=s.b_address; m['In-Reply-To']='<root@x>'; m['Subject']=subject; m.set_content(body); return parse_inbound(m.as_bytes(),ref)
        tg=Tg(d,[]); out=Out(); svc=BridgeService(s,st,tg,In([mail('r1','Re:','answer'),mail('c1','MAILTG OFF','')]),out)
        asyncio.run(svc.run_mailbox_cycle()); assert tg.posts==[(d.dialog_id,'answer')] and st.is_consumed('r1')
        assert not st.bridge_state().enabled and st.is_consumed('c1') and len(out.notices)==1

def test_tail_bootstrap_is_silent(tmp_path):
    s=settings(tmp_path,False); d=DialogRef('-1001',SourceType.CHANNEL,whitelisted=True); out=Out()
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); asyncio.run(BridgeService(s,st,Tg(d,[TgMessage(5,d.dialog_id,datetime.now(timezone.utc))]),In(),out).run_inbound_cycle())
        assert st.get_cursor(d).last_id==5 and not out.sent

class ScaleTg:
    # counts NETWORK round-trips (fetch_since); the top-id gate must keep this O(active).
    def __init__(self,dialogs): self.dialogs=dialogs; self.fetch_calls=0
    async def list_tracked_dialogs(self): return self.dialogs
    async def fetch_since(self,dialog,last_id,limit): self.fetch_calls+=1; return []
    async def download_media(self,m): return []
    async def post_as_user(self,d,t): return 1

def test_polling_is_sublinear_in_dialog_count(tmp_path):
    # TKT-12 load-profile invariant: a cycle over N idle dialogs must not fetch each one.
    # Only dialogs whose top message id is ahead of the cursor (active) hit the network.
    s=settings(tmp_path); N=1000; active=5
    dialogs=[DialogRef(f"u{i}",SourceType.DM,top_id=(200 if i<active else 100)) for i in range(N)]
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True)
        for d in dialogs: st.advance_cursor(d,100)   # everyone caught up to id=100
        tg=ScaleTg(dialogs); asyncio.run(BridgeService(s,st,tg,In(),Out()).run_inbound_cycle())
        assert tg.fetch_calls==active, f"expected O(active)={active} network fetches, got {tg.fetch_calls} (O(N) regression)"
