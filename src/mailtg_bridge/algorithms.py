from __future__ import annotations
import random, re
from datetime import datetime, timedelta, timezone
from .domain import BackoffDecision, DialogBatch, DialogRef, MentionPolicy, SourceType, TgMessage
from .errors import FloodWait

def is_addressed(message: TgMessage, dialog: DialogRef, whitelist: set[str] | frozenset[str],
                 policy: MentionPolicy, mention_list: set[str] | frozenset[str], username: str | None=None) -> bool:
    if dialog.source_type is SourceType.DM: return True
    ids={dialog.dialog_id}
    if dialog.username: ids.add("@"+dialog.username.lower().lstrip("@"))
    if dialog.topic_id is not None: ids.add(f"{dialog.dialog_id}:{dialog.topic_id}")
    if ids & set(whitelist): return True
    textual=bool(username and re.search(rf"(?<![\w@])@{re.escape(username.lstrip('@'))}\b",message.text,re.I))
    mentioned=message.mentioned or textual
    if policy is MentionPolicy.ALL: return mentioned
    if policy is MentionPolicy.SELECTED: return mentioned and bool(ids & set(mention_list))
    return bool(ids & set(mention_list))

def make_dialog_batch(dialog: DialogRef, messages, high_watermark: int | None=None) -> DialogBatch:
    ordered=tuple(sorted(messages,key=lambda m:m.msg_id))
    hw=high_watermark if high_watermark is not None else max((m.msg_id for m in ordered),default=0)
    return DialogBatch(dialog,ordered,hw)

def next_backoff(error: Exception, failures: int, minimum: int, maximum: int, now: datetime,
                 jitter: float=0.1, rng=random.random) -> BackoffDecision:
    count=failures+1
    if isinstance(error,FloodWait): delay=max(minimum,error.wait_seconds)
    else:
        base=min(maximum,minimum*(2**max(0,count-1)))
        delay=min(maximum,max(minimum,base*(1+jitter*rng())))
    return BackoffDecision(now+timedelta(seconds=delay),count)

def build_deeplink(dialog: DialogRef, msg_id: int) -> str | None:
    if dialog.source_type is SourceType.DM: return None
    suffix=f"/{dialog.topic_id}/{msg_id}" if dialog.topic_id is not None else f"/{msg_id}"
    if dialog.username: return f"https://t.me/{dialog.username.lstrip('@')}{suffix}"
    peer=str(dialog.peer_id if dialog.peer_id is not None else dialog.dialog_id)
    internal=peer[4:] if peer.startswith("-100") else peer.lstrip("-")
    return f"https://t.me/c/{internal}{suffix}"
