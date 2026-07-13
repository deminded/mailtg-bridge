from __future__ import annotations

import json, os, re, stat
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from email.utils import parseaddr

from .domain import BotPolicy, MentionPolicy
from .errors import ConfigError

class SecurityMode(str, Enum):
    SSL = "ssl"
    STARTTLS = "starttls"

class BootstrapMode(str, Enum):
    TAIL = "tail"
    HISTORY = "history"

def _env_file(path: str | Path) -> dict[str, str]:
    result: dict[str, str] = {}
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    return result

def _email(value: str, key: str) -> str:
    address = parseaddr(value)[1].strip().lower()
    if not address or address != value.strip().lower() or "@" not in address:
        raise ConfigError(f"{key} must be a plain valid email address")
    return address

def canonical_source(value: str) -> str:
    value = value.strip()
    if not value or not re.fullmatch(r"(?:@[A-Za-z0-9_]{3,}|-?\d+)(?::\d+)?", value):
        raise ConfigError("invalid source identifier")
    return value.lower() if value.startswith("@") else value

@dataclass(frozen=True, slots=True)
class Settings:
    tg_api_id: int; tg_api_hash: str; tg_session_path: Path
    b_address: str; b_username: str; b_password: str
    b_imap_host: str; b_imap_port: int; b_imap_security: SecurityMode
    b_smtp_host: str; b_smtp_port: int; b_smtp_security: SecurityMode
    u_address: str; whitelist: tuple[str, ...]; mention_policy: MentionPolicy
    mention_list: tuple[str, ...]; state_db_path: Path; lock_path: Path; temp_dir: Path
    tg_fetch_limit: int = 100; attachment_threshold_bytes: int = 10*1024*1024
    email_size_limit_bytes: int = 24*1024*1024; collect_interval_seconds: int = 60
    send_interval_seconds: int = 30; backoff_min_seconds: int = 30
    backoff_max_seconds: int = 3600; command_token: str = ""; timezone: str = "America/Phoenix"
    retention_seconds: int = 90*86400; retention_max_ledger: int = 50000
    retention_max_consumed: int = 50000; retention_max_echo: int = 10000
    echo_retention_seconds: int = 7*86400; bootstrap_mode: BootstrapMode = BootstrapMode.TAIL
    discover_all_dialogs: bool = False; log_level: str = "INFO"
    bot_policy: BotPolicy = BotPolicy.ALL; bot_list: tuple[str, ...] = ()
    save_sent_copy: bool = True; sent_folder: str = "Sent"

    @classmethod
    def from_env(cls, path: str | Path | None = None, environ: dict[str,str] | None = None) -> "Settings":
        data = dict(os.environ if environ is None else environ)
        if path:
            data = {**_env_file(path), **data}
        required = ["TG_API_ID","TG_API_HASH","TG_SESSION_PATH","B_ADDRESS","B_USERNAME","B_PASSWORD",
                    "B_IMAP_HOST","B_SMTP_HOST","U_ADDRESS","STATE_DB_PATH","LOCK_PATH","TEMP_DIR"]
        missing = [k for k in required if not data.get(k)]
        if missing: raise ConfigError("missing required settings: " + ", ".join(missing))
        def integer(key: str, default: int) -> int:
            try: value = int(data.get(key, default))
            except ValueError as exc: raise ConfigError(f"{key} must be an integer") from exc
            if value <= 0: raise ConfigError(f"{key} must be positive")
            return value
        def absolute(key: str) -> Path:
            p=Path(data[key]);
            if not p.is_absolute(): raise ConfigError(f"{key} must be absolute")
            return p
        try:
            wl=tuple(canonical_source(x) for x in json.loads(data.get("WHITELIST_JSON","[]")))
            ml=tuple(canonical_source(x) for x in json.loads(data.get("MENTION_LIST_JSON","[]")))
            imsec=SecurityMode(data.get("B_IMAP_SECURITY","ssl").lower())
            smsec=SecurityMode(data.get("B_SMTP_SECURITY","ssl").lower())
            mp=MentionPolicy(data.get("MENTION_POLICY","selected").lower())
            bm=BootstrapMode(data.get("BOOTSTRAP_MODE","tail").lower())
            bp=BotPolicy(data.get("BOT_POLICY","all").lower())
            bl=tuple(canonical_source(x) for x in json.loads(data.get("BOT_LIST_JSON","[]")))
        except (ValueError, TypeError, json.JSONDecodeError) as exc: raise ConfigError("invalid enum or JSON setting") from exc
        save_sent=data.get("SAVE_SENT_COPY","true").lower() in {"1","true","yes"}
        sent_folder=(data.get("SENT_FOLDER","Sent") or "Sent").strip()
        s=cls(integer("TG_API_ID",0),data["TG_API_HASH"],absolute("TG_SESSION_PATH"),_email(data["B_ADDRESS"],"B_ADDRESS"),
            data["B_USERNAME"],data["B_PASSWORD"],data["B_IMAP_HOST"],integer("B_IMAP_PORT",993),imsec,
            data["B_SMTP_HOST"],integer("B_SMTP_PORT",465),smsec,_email(data["U_ADDRESS"],"U_ADDRESS"),wl,mp,ml,
            absolute("STATE_DB_PATH"),absolute("LOCK_PATH"),absolute("TEMP_DIR"),integer("TG_FETCH_LIMIT",100),
            integer("ATTACHMENT_THRESHOLD_BYTES",10*1024*1024),integer("EMAIL_SIZE_LIMIT_BYTES",24*1024*1024),
            integer("COLLECT_INTERVAL_SECONDS",60),integer("SEND_INTERVAL_SECONDS",30),integer("BACKOFF_MIN_SECONDS",30),
            integer("BACKOFF_MAX_SECONDS",3600),data.get("COMMAND_TOKEN",""),data.get("TIMEZONE","America/Phoenix"),
            integer("RETENTION_SECONDS",90*86400),integer("RETENTION_MAX_LEDGER",50000),integer("RETENTION_MAX_CONSUMED",50000),
            integer("RETENTION_MAX_ECHO",10000),integer("ECHO_RETENTION_SECONDS",7*86400),bm,
            data.get("DISCOVER_ALL_DIALOGS","").lower() in {"1","true","yes"},data.get("LOG_LEVEL","INFO").upper(),
            bp,bl,save_sent,sent_folder)
        if s.attachment_threshold_bytes >= s.email_size_limit_bytes: raise ConfigError("attachment threshold must be below email size limit")
        if s.echo_retention_seconds > s.retention_seconds: raise ConfigError("echo retention cannot exceed retention")
        if s.backoff_min_seconds > s.backoff_max_seconds: raise ConfigError("backoff min cannot exceed max")
        return s

def assert_private(path: Path, directory: bool = False) -> None:
    if not path.exists(): return
    bad = stat.S_IMODE(path.stat().st_mode) & (0o077 if directory else 0o177)
    if bad: raise ConfigError(f"unsafe permissions: {path}")
