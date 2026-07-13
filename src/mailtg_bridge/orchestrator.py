from __future__ import annotations
import asyncio, logging
from datetime import datetime, timezone
from .algorithms import is_addressed, make_dialog_batch, next_backoff
from .commands import parse_command
from .config import BootstrapMode, Settings
from .domain import SentMail
from .errors import FloodWait, PeerNotFound, SessionInvalid, Transient
from .mail_in import MailClassifier

log=logging.getLogger(__name__)

class BridgeService:
    def __init__(self,settings: Settings,store,tg,mail_in,mail_out,composer=None,clock=None):
        self.s=settings; self.store=store; self.tg=tg; self.mail_in=mail_in; self.mail_out=mail_out
        self.composer=composer or mail_out; self.clock=clock
        self.classifier=MailClassifier(settings.u_address,settings.b_address); self._stop=False
    def now(self): return self.clock.now() if self.clock else datetime.now(timezone.utc)
    def delivery_allowed(self): return self.store.bridge_state().enabled and self.store.session_health().valid
    def _due(self,scope):
        b=self.store.backoff(scope); return not b or b.not_before<=self.now()
    def record_failure(self,scope,error):
        old=self.store.backoff(scope); self.store.set_backoff(scope,next_backoff(error,old.failures if old else 0,self.s.backoff_min_seconds,self.s.backoff_max_seconds,self.now()))
    async def invalidate_session(self):
        health=self.store.session_health()
        if health.valid: self.store.set_session(False,False)
        if not self.store.session_health().notified:
            try: self.mail_out.send_notice("mailtg-bridge: Telegram session invalid","Telegram authorization must be restored with mailtg-bridge setup.")
            except Transient as exc: self.record_failure("mail:session-notice",exc); return
            self.store.mark_session_notified(); self.store.clear_backoff("mail:session-notice")
    async def run_inbound_cycle(self):
        if not self.delivery_allowed() or not self._due("tg:list"): return
        try: dialogs=await self.tg.list_tracked_dialogs(); self.store.clear_backoff("tg:list")
        except SessionInvalid: await self.invalidate_session(); return
        except (FloodWait,Transient) as exc: self.record_failure("tg:list",exc); return
        for dialog in dialogs:
            scope=f"tg:{dialog.dialog_id}"
            if not self._due(scope): continue
            cursor=self.store.get_cursor(dialog)
            if dialog.top_id is not None and dialog.top_id<=cursor.last_id:
                self.store.clear_backoff(scope); continue
            try:
                messages=list(await self.tg.fetch_since(dialog,cursor.last_id,self.s.tg_fetch_limit))
                if not messages: self.store.clear_backoff(scope); continue
                high=max(m.msg_id for m in messages)
                if cursor.last_id==0 and self.s.bootstrap_mode is BootstrapMode.TAIL:
                    self.store.advance_cursor(dialog,high); self.store.clear_backoff(scope); continue
                selected=[m for m in messages if m.msg_id>cursor.last_id and not self.store.is_echo(dialog.dialog_id,m.msg_id)
                    and is_addressed(m,dialog,set(self.s.whitelist),self.s.mention_policy,set(self.s.mention_list))]
                if not selected: self.store.advance_cursor(dialog,high); self.store.clear_backoff(scope); continue
                batch=make_dialog_batch(dialog,selected,high); downloaded={}
                try:
                    for message in selected:
                        if message.media: downloaded[message.msg_id]=await self.tg.download_media(message)
                    drafts=self.composer.compose_batch(batch,downloaded); sent=[]
                    for draft in drafts:
                        result=self.mail_out.send(draft); sent.append(SentMail(result.message_id,dialog.dialog_id,dialog.source_type,result.sender))
                    self.store.commit_delivery(dialog,sent,high); self.store.clear_backoff(scope)
                finally:
                    for items in downloaded.values():
                        for item in items:
                            try: item.path.unlink(missing_ok=True)
                            except OSError: pass
            except SessionInvalid: await self.invalidate_session(); return
            except PeerNotFound: log.warning("telegram peer unavailable",extra={"operation":"fetch"})
            except (FloodWait,Transient) as exc: self.record_failure(scope,exc)
    async def run_mailbox_cycle(self):
        if not self._due("mail:poll"): return
        try: mails=self.mail_in.poll(); self.store.clear_backoff("mail:poll")
        except Transient as exc: self.record_failure("mail:poll",exc); return
        for mail in mails:
            if self.store.is_consumed(mail.mail_ref) or not self.classifier.trusted(mail): continue
            parent=self.store.ledger_dialog(self.classifier.parent_ids(mail))
            if not parent: continue
            command=parse_command(mail.subject,mail.body_text,self.s.command_token)
            if command:
                self.store.set_bridge_enabled(command.enabled,mail.mail_ref)
                state="ON" if command.enabled else "OFF"; kind=f"command:{mail.mail_ref}"
                self.store.queue_notice(kind,f"mailtg-bridge is {state}",f"Bridge state is now {state}.")
                continue
            if not self.delivery_allowed() or not mail.body_text: continue
            try:
                posted=await self.tg.post_as_user(parent,mail.body_text)
                self.store.commit_reply(mail.mail_ref,parent,posted)
            except SessionInvalid: await self.invalidate_session(); break
            except (FloodWait,Transient) as exc: self.record_failure(f"tg:post:{parent}",exc)
        await self.flush_notices()
        if not self.store.session_health().valid: await self.invalidate_session()
    async def flush_notices(self):
        for notice in self.store.pending_notices():
            try: self.mail_out.send_notice(notice["subject"],notice["body"]); self.store.delete_notice(notice["kind"])
            except Transient as exc: self.record_failure(f"mail:notice:{notice['kind']}",exc)
    async def run_once(self,kind="all"):
        if kind in {"all","inbound"}: await self.run_inbound_cycle()
        if kind in {"all","mailbox"}: await self.run_mailbox_cycle()
    async def run(self):
        next_in=next_mail=self.now().timestamp()
        while not self._stop:
            now=self.now().timestamp()
            if now>=next_in: await self.run_inbound_cycle(); next_in=now+self.s.collect_interval_seconds
            if now>=next_mail: await self.run_mailbox_cycle(); next_mail=now+self.s.send_interval_seconds
            await asyncio.sleep(max(.1,min(next_in,next_mail)-self.now().timestamp()))
    def stop(self): self._stop=True
