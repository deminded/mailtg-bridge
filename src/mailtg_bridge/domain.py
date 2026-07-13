from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path


class SourceType(str, Enum):
    DM = "dm"
    CHANNEL = "channel"
    GROUP = "group"
    TOPIC = "topic"

class MentionPolicy(str, Enum):
    ALL = "all"
    SELECTED = "selected"
    FORCED_LIST = "forced_list"

class BotPolicy(str, Enum):
    NONE = "none"        # never bridge messages authored by bots
    ALL = "all"          # treat bot messages like any other (v0.1 behaviour)
    SELECTED = "selected"  # only bots whose @username is in bot_list

class MailKind(str, Enum):
    REPLY = "reply"
    COMMAND = "command"
    IGNORE = "ignore"

@dataclass(frozen=True, slots=True)
class DialogRef:
    dialog_id: str
    source_type: SourceType
    title: str = ""
    username: str | None = None
    peer_id: int | None = None
    topic_id: int | None = None
    source_tag: str = ""
    whitelisted: bool = False
    top_id: int | None = None

@dataclass(frozen=True, slots=True)
class Cursor:
    dialog_id: str
    last_id: int = 0

@dataclass(frozen=True, slots=True)
class Sender:
    display_name: str = ""
    username: str | None = None
    sender_id: int | None = None
    is_bot: bool = False

@dataclass(frozen=True, slots=True)
class MessageEntity:
    kind: str
    offset: int
    length: int
    url: str | None = None

@dataclass(frozen=True, slots=True)
class MediaRef:
    media_id: str
    filename: str = "media"
    content_type: str = "application/octet-stream"
    size: int | None = None

@dataclass(frozen=True, slots=True)
class DownloadedMedia:
    ref: MediaRef
    path: Path
    size: int

@dataclass(frozen=True, slots=True)
class TgMessage:
    msg_id: int
    dialog_id: str
    date: datetime
    sender: Sender = field(default_factory=Sender)
    text: str = ""
    entities: tuple[MessageEntity, ...] = ()
    media: tuple[MediaRef, ...] = ()
    mentioned: bool = False
    reply_quote: str | None = None

@dataclass(frozen=True, slots=True)
class DialogBatch:
    dialog: DialogRef
    messages: tuple[TgMessage, ...]
    high_watermark: int

@dataclass(frozen=True, slots=True)
class RenderedMessage:
    msg_id: int
    text: str
    html: str

@dataclass(frozen=True, slots=True)
class MailDraft:
    message_id: str
    to: str
    subject: str
    raw: bytes
    dialog_id: str | None = None

@dataclass(frozen=True, slots=True)
class SentMail:
    message_id: str
    dialog_id: str
    source_type: SourceType
    sender: str = ""

@dataclass(frozen=True, slots=True)
class InboundMail:
    mail_ref: str
    from_addr: str
    recipients: tuple[str, ...]
    subject: str
    body_text: str
    message_id: str = ""
    in_reply_to: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    auto_or_loop: bool = False
    has_attachments: bool = False

@dataclass(frozen=True, slots=True)
class BridgeState:
    enabled: bool
    updated_at: datetime

@dataclass(frozen=True, slots=True)
class SessionHealth:
    valid: bool
    notified: bool
    updated_at: datetime

@dataclass(frozen=True, slots=True)
class BackoffDecision:
    not_before: datetime
    failures: int

def utcnow() -> datetime:
    return datetime.now(timezone.utc)
