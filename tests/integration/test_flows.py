from datetime import datetime, timedelta, timezone
import asyncio
from email import message_from_bytes
from email.message import EmailMessage
from email.policy import default
import pytest
from mailtg_bridge.config import Settings
from mailtg_bridge.domain import *
from mailtg_bridge.errors import MediaUnavailable
from mailtg_bridge.mail_in import parse_inbound
from mailtg_bridge.mail_out import EmailComposer
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

def test_reply_respects_scoped_backoff(tmp_path):
    # DEFECT-1: record_failure wrote a scoped tg:post:<dialog> backoff on FloodWait/Transient,
    # but nothing checked it before the next attempt -> retries busy-looped every mailbox tact
    # instead of waiting out the recorded delay (run_inbound_cycle already gates this way per dialog).
    s=settings(tmp_path); d=DialogRef('-1001',SourceType.CHANNEL)
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); st.get_cursor(d); st.commit_delivery(d,[SentMail('<root@x>',d.dialog_id,d.source_type)],1)
        st.set_backoff(f"tg:post:{d.dialog_id}",BackoffDecision(datetime.now(timezone.utc)+timedelta(seconds=60),1))
        def mail(ref,subject,body):
            m=EmailMessage(); m['From']=s.u_address; m['To']=s.b_address; m['In-Reply-To']='<root@x>'; m['Subject']=subject; m.set_content(body); return parse_inbound(m.as_bytes(),ref)
        tg=Tg(d,[]); out=Out(); svc=BridgeService(s,st,tg,In([mail('r1','Re:','answer')]),out)
        asyncio.run(svc.run_mailbox_cycle())
        assert tg.posts==[] and not st.is_consumed('r1'), "backoff active: must not publish nor consume yet"
        st.clear_backoff(f"tg:post:{d.dialog_id}")
        asyncio.run(svc.run_mailbox_cycle())
        assert tg.posts==[(d.dialog_id,'answer')] and st.is_consumed('r1'), "backoff elapsed: retry publishes and consumes"

def test_plain_reply_to_notice_has_no_dialog_and_is_ignored(tmp_path):
    # DEFECT-2 investigated and resolved as NOT a defect: OE-SOURCES' "delivery OR confirmation"
    # trust wording is the command predicate (is_bridge_message, exercised above for MAILTG ON/OFF).
    # A plain reply (not a command) still resolves its *target dialog* strictly via the delivery
    # ledger (cap-resolve-ledger, -> scn-outbound-reply step 5) — a notice is never bound to a
    # dialog, so a reply to one correctly finds no ledger record and is not published (the
    # "не-bridged письмо" alt-flow), not left dangling on some guessed dialog.
    s=settings(tmp_path); d=DialogRef('-1001',SourceType.CHANNEL)
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); st.record_notice_sent('<notice-off@x>')  # confirmation the bridge sent, no dialog
        m=EmailMessage(); m['From']=s.u_address; m['To']=s.b_address; m['In-Reply-To']='<notice-off@x>'
        m['Subject']='Re: mailtg-bridge is OFF'; m.set_content('thanks, just a reply')
        tg=Tg(d,[]); out=Out(); svc=BridgeService(s,st,tg,In([parse_inbound(m.as_bytes(),'r1')]),out)
        asyncio.run(svc.run_mailbox_cycle())
        assert tg.posts==[], "reply to a notice has no dialog to route to: must not publish"

def test_command_reply_to_notice_and_reject_unknown(tmp_path):
    # Live test: user replied "MAILTG ON" to the OFF *confirmation*, whose id is not in the
    # delivery ledger. A command must be trusted when it replies to any bridge-sent mail
    # (delivery OR notice), but rejected when it replies to something the bridge never sent.
    s=settings(tmp_path)
    def cmd(ref,irt,body):
        m=EmailMessage(); m['From']=s.u_address; m['To']=s.b_address; m['In-Reply-To']=irt
        m['Subject']='Re: mailtg-bridge is OFF'; m.set_content(body); return parse_inbound(m.as_bytes(),ref)
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); st.set_bridge_enabled(False)
        st.record_notice_sent('<notice-off@x>')            # the confirmation the bridge sent
        out=Out(); svc=BridgeService(s,st,Tg(DialogRef('-1001',SourceType.CHANNEL),[]),
            In([cmd('u-unknown','<stranger@x>','MAILTG ON'), cmd('u-notice','<notice-off@x>','MAILTG ON')]),out)
        asyncio.run(svc.run_mailbox_cycle())
        assert st.bridge_state().enabled is True, "reply to a bridge notice must re-enable"
        assert st.is_consumed('u-notice') and not st.is_consumed('u-unknown'), "unknown-parent command ignored"

def test_tail_bootstrap_is_silent(tmp_path):
    s=settings(tmp_path,False); d=DialogRef('-1001',SourceType.CHANNEL,whitelisted=True); out=Out()
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); asyncio.run(BridgeService(s,st,Tg(d,[TgMessage(5,d.dialog_id,datetime.now(timezone.utc))]),In(),out).run_inbound_cycle())
        assert st.get_cursor(d).last_id==5 and not out.sent

def test_media_unavailable_download_still_delivers_with_marker(tmp_path):
    # DEFECT-5: MediaUnavailable is a bare BridgeError (not Transient), so before the fix it
    # propagated out of run_inbound_cycle uncaught -> the whole inbound tact crashed instead of
    # degrading to a marker and still delivering the text (fn-media-in-email/OE-EVIDENCE AC-06).
    class FlakyTg(Tg):
        async def download_media(self,m): raise MediaUnavailable("file reference expired")
    s=settings(tmp_path); d=DialogRef('-1001',SourceType.CHANNEL,whitelisted=True)
    m=TgMessage(2,d.dialog_id,datetime.now(timezone.utc),text='look',media=(MediaRef('1','x.png','image/png',8),))
    with SQLiteStore(s.state_db_path) as st:
        st.set_session(True); out=Out()
        svc=BridgeService(s,st,FlakyTg(d,[m]),In(),out,composer=EmailComposer(s))
        asyncio.run(svc.run_inbound_cycle())  # must not raise
        assert len(out.sent)==1 and st.get_cursor(d).last_id==2, "text still delivered, cursor still advances"
        html=message_from_bytes(out.sent[0].raw,policy=default).get_body(('html',)).get_content()
        assert 'media unavailable' in html.lower(), f"expected an explicit marker, got: {html!r}"

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
