from __future__ import annotations
import os, re
from datetime import timezone
from pathlib import Path
from .config import Settings
from .domain import DialogRef, DownloadedMedia, MediaRef, MessageEntity, Sender, SourceType, TgMessage
from .errors import FloodWait, MediaUnavailable, PeerNotFound, SessionInvalid, Transient

def classify_error(exc: Exception) -> Exception:
    name=type(exc).__name__
    if name=="FloodWaitError": return FloodWait(getattr(exc,"seconds",0))
    if name in {"AuthKeyError","AuthKeyUnregisteredError","SessionRevokedError","UserDeactivatedError","UnauthorizedError"}: return SessionInvalid("Telegram session is invalid")
    if name in {"UsernameInvalidError","UsernameNotOccupiedError","ChannelInvalidError","ChannelPrivateError","PeerIdInvalidError"}: return PeerNotFound("Telegram peer unavailable")
    if name in {"FileReferenceExpiredError","FileIdInvalidError","MediaEmptyError"}: return MediaUnavailable("Telegram media unavailable")
    if isinstance(exc,(OSError,TimeoutError,ConnectionError)) or name in {"ServerError","RpcCallFailError","TimedOutError"}: return Transient("Telegram operation failed transiently")
    return exc

def parse_source(source: str) -> tuple[str,int|None]:
    peer,sep,topic=source.partition(":"); return peer,int(topic) if sep else None

class TelethonGateway:
    def __init__(self, settings: Settings, client=None):
        self.s=settings
        if client is None:
            try: from telethon import TelegramClient
            except ImportError as exc: raise RuntimeError("Telethon is required for Telegram operations") from exc
            client=TelegramClient(str(settings.tg_session_path),settings.tg_api_id,settings.tg_api_hash)
        self.client=client
    async def connect(self):
        try: await self.client.connect()
        except Exception as exc: raise classify_error(exc) from exc
    async def close(self): await self.client.disconnect()
    async def _entity(self,source):
        peer,_=parse_source(source)
        try: return await self.client.get_entity(int(peer) if re.fullmatch(r"-?\d+",peer) else peer)
        except Exception as exc: raise classify_error(exc) from exc
    async def list_tracked_dialogs(self):
        sources=set(self.s.whitelist)|set(self.s.mention_list)
        result=[]
        try:
            if self.s.mention_policy.value=="all" and self.s.discover_all_dialogs:
                async for d in self.client.iter_dialogs():
                    tid=d.message.id if getattr(d,"message",None) else None
                    if getattr(d,"is_user",False): result.append(self._dialog(d.entity,None,True,tid))
                    elif getattr(d,"is_channel",False) or getattr(d,"is_group",False): result.append(self._dialog(d.entity,None,False,tid))
            else:
                async for d in self.client.iter_dialogs():
                    if getattr(d,"is_user",False): result.append(self._dialog(d.entity,None,True,d.message.id if getattr(d,"message",None) else None))
                for source in sorted(sources):
                    peer,topic=parse_source(source); entity=await self._entity(peer); result.append(self._dialog(entity,topic,source in self.s.whitelist))
            unique={d.dialog_id:d for d in result}; return list(unique.values())
        except Exception as exc: raise classify_error(exc) from exc
    def _dialog(self,e,topic,whitelisted,top_id=None):
        eid=getattr(e,"id",0); is_user=type(e).__name__=="User" or getattr(e,"bot",None) is not None
        is_channel=getattr(e,"broadcast",False); source=SourceType.DM if is_user else SourceType.CHANNEL if is_channel else SourceType.TOPIC if topic else SourceType.GROUP
        did=str(eid if is_user else int(f"-100{eid}")); did=f"{did}:{topic}" if topic else did
        return DialogRef(did,source,getattr(e,"title",None) or " ".join(filter(None,[getattr(e,"first_name",None),getattr(e,"last_name",None)])),getattr(e,"username",None),int(str(did).split(':')[0]),topic,str(did),whitelisted,top_id)
    async def fetch_since(self,dialog,last_id,limit):
        entity=await self._entity(dialog.dialog_id.split(":")[0]); found=[]
        try:
            kwargs=dict(min_id=last_id,limit=limit)
            if dialog.topic_id: kwargs["reply_to"]=dialog.topic_id
            async for m in self.client.iter_messages(entity,**kwargs): found.append(self._message(dialog,m))
            return sorted(found,key=lambda x:x.msg_id)
        except Exception as exc: raise classify_error(exc) from exc
    def _message(self,d,m):
        sender_obj=getattr(m,"sender",None); sender=Sender(getattr(sender_obj,"first_name",None) or getattr(sender_obj,"title","") or "",getattr(sender_obj,"username",None),getattr(sender_obj,"id",None))
        entities=tuple(MessageEntity(type(e).__name__.removeprefix("MessageEntity").lower(),e.offset,e.length,getattr(e,"url",None)) for e in (getattr(m,"entities",None) or ()))
        media=()
        if getattr(m,"media",None):
            file=getattr(m,"file",None); media=(MediaRef(str(m.id),getattr(file,"name",None) or f"media-{m.id}",getattr(file,"mime_type",None) or "application/octet-stream",getattr(file,"size",None)),)
        return TgMessage(m.id,d.dialog_id,m.date.astimezone(timezone.utc),sender,m.message or "",entities,media,bool(getattr(m,"mentioned",False)))
    async def download_media(self,message):
        result=[]
        try:
            raw=await self.client.get_messages(int(message.dialog_id.split(':')[0]),ids=message.msg_id)
            path=await self.client.download_media(raw,file=str(self.s.temp_dir)+os.sep)
            if path and message.media:
                p=Path(path); result.append(DownloadedMedia(message.media[0],p,p.stat().st_size))
            return result
        except Exception as exc: raise classify_error(exc) from exc
    async def post_as_user(self,dialog_id,text):
        try:
            entity=await self._entity(dialog_id.split(':')[0]); sent=await self.client.send_message(entity,text,reply_to=int(dialog_id.split(':')[1]) if ':' in dialog_id else None); return int(sent.id)
        except Exception as exc: raise classify_error(exc) from exc

async def authorize_interactive(settings: Settings, phone: str, code_callback, password_callback, reauthorize=False):
    from telethon import TelegramClient
    from telethon.errors import SessionPasswordNeededError
    client=TelegramClient(str(settings.tg_session_path),settings.tg_api_id,settings.tg_api_hash); await client.connect()
    try:
        if await client.is_user_authorized() and not reauthorize: return await client.get_me()
        await client.send_code_request(phone)
        try: await client.sign_in(phone,code_callback())
        except SessionPasswordNeededError: await client.sign_in(password=password_callback())
        me=await client.get_me()
        if not me: raise SessionInvalid("authorization did not yield an account")
        return me
    finally:
        await client.disconnect()
        for candidate in (settings.tg_session_path,Path(str(settings.tg_session_path)+".session")):
            if candidate.exists(): os.chmod(candidate,0o600)
