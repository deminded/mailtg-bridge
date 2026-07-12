from __future__ import annotations

import os, sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from .domain import BackoffDecision, BridgeState, Cursor, DialogRef, SentMail, SessionHealth, SourceType

SCHEMA_VERSION = 1

class SQLiteStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(self.path.parent, 0o700)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        os.chmod(self.path, 0o600)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=FULL")
        self.db.execute("PRAGMA busy_timeout=5000")
        self._migrate()

    def close(self): self.db.close()
    def __enter__(self): return self
    def __exit__(self, *_): self.close()
    @staticmethod
    def _iso(value: datetime | None = None) -> str:
        return (value or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat()
    @contextmanager
    def transaction(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
        except BaseException:
            self.db.rollback(); raise
        else: self.db.commit()

    def _migrate(self):
        with self.transaction():
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS dialog_cursor(dialog_id TEXT PRIMARY KEY, source_type TEXT NOT NULL,
              last_id INTEGER NOT NULL CHECK(last_id>=0), whitelisted INTEGER NOT NULL, source_tag TEXT NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS mail_ledger(message_id TEXT PRIMARY KEY, dialog_id TEXT NOT NULL,
              source_type TEXT NOT NULL, sender TEXT NOT NULL, delivered_at TEXT NOT NULL,
              FOREIGN KEY(dialog_id) REFERENCES dialog_cursor(dialog_id));
            CREATE TABLE IF NOT EXISTS consumed_mail(mail_ref TEXT PRIMARY KEY, consumed_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS posted_echo(dialog_id TEXT NOT NULL, posted_msg_id INTEGER NOT NULL,
              posted_at TEXT NOT NULL, PRIMARY KEY(dialog_id,posted_msg_id));
            CREATE TABLE IF NOT EXISTS bridge_state(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              enabled INTEGER NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS session_health(singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              valid INTEGER NOT NULL, notified INTEGER NOT NULL, updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS runtime_backoff(scope TEXT PRIMARY KEY, not_before TEXT NOT NULL,
              failures INTEGER NOT NULL CHECK(failures>=0), updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS pending_notice(kind TEXT PRIMARY KEY, subject TEXT NOT NULL, body TEXT NOT NULL,
              created_at TEXT NOT NULL);
            """)
            now=self._iso()
            self.db.execute("INSERT OR IGNORE INTO meta VALUES('schema_version',?)",(str(SCHEMA_VERSION),))
            self.db.execute("INSERT OR IGNORE INTO bridge_state VALUES(1,1,?)",(now,))
            self.db.execute("INSERT OR IGNORE INTO session_health VALUES(1,0,0,?)",(now,))

    def _ensure_dialog(self, d: DialogRef):
        self.db.execute("""INSERT INTO dialog_cursor VALUES(?,?,?,?,?,?)
          ON CONFLICT(dialog_id) DO UPDATE SET source_type=excluded.source_type,
          whitelisted=excluded.whitelisted,source_tag=excluded.source_tag,updated_at=excluded.updated_at""",
          (d.dialog_id,d.source_type.value,0,int(d.whitelisted),d.source_tag,self._iso()))

    def get_cursor(self, dialog: DialogRef) -> Cursor:
        with self.transaction(): self._ensure_dialog(dialog)
        row=self.db.execute("SELECT last_id FROM dialog_cursor WHERE dialog_id=?",(dialog.dialog_id,)).fetchone()
        return Cursor(dialog.dialog_id,row[0])

    def advance_cursor(self, dialog: DialogRef, high_watermark: int):
        if high_watermark < 0: raise ValueError("negative cursor")
        with self.transaction():
            self._ensure_dialog(dialog)
            self.db.execute("UPDATE dialog_cursor SET last_id=max(last_id,?),updated_at=? WHERE dialog_id=?",
                            (high_watermark,self._iso(),dialog.dialog_id))

    def commit_delivery(self, dialog: DialogRef, sent: Sequence[SentMail], high_watermark: int):
        if not sent: raise ValueError("delivery requires ledger records")
        with self.transaction():
            self._ensure_dialog(dialog)
            now=self._iso()
            for item in sent:
                if item.dialog_id != dialog.dialog_id: raise ValueError("ledger dialog mismatch")
                self.db.execute("INSERT INTO mail_ledger VALUES(?,?,?,?,?)",
                    (item.message_id,item.dialog_id,item.source_type.value,item.sender,now))
            self.db.execute("UPDATE dialog_cursor SET last_id=max(last_id,?),updated_at=? WHERE dialog_id=?",
                            (high_watermark,now,dialog.dialog_id))

    def ledger_dialog(self, message_ids: Sequence[str]) -> str | None:
        for mid in message_ids:
            row=self.db.execute("SELECT dialog_id FROM mail_ledger WHERE message_id=?",(mid,)).fetchone()
            if row: return str(row[0])
        return None
    def is_consumed(self, ref: str) -> bool:
        return self.db.execute("SELECT 1 FROM consumed_mail WHERE mail_ref=?",(ref,)).fetchone() is not None
    def mark_consumed(self, ref: str):
        self.db.execute("INSERT OR IGNORE INTO consumed_mail VALUES(?,?)",(ref,self._iso()))
    def is_echo(self, dialog_id: str, msg_id: int) -> bool:
        return self.db.execute("SELECT 1 FROM posted_echo WHERE dialog_id=? AND posted_msg_id=?",(dialog_id,msg_id)).fetchone() is not None
    def commit_reply(self, ref: str, dialog_id: str, msg_id: int):
        with self.transaction():
            now=self._iso(); self.db.execute("INSERT OR IGNORE INTO posted_echo VALUES(?,?,?)",(dialog_id,msg_id,now))
            self.db.execute("INSERT OR IGNORE INTO consumed_mail VALUES(?,?)",(ref,now))

    def bridge_state(self) -> BridgeState:
        r=self.db.execute("SELECT * FROM bridge_state WHERE singleton=1").fetchone()
        return BridgeState(bool(r["enabled"]),datetime.fromisoformat(r["updated_at"]))
    def set_bridge_enabled(self, enabled: bool, consumed_ref: str | None = None):
        with self.transaction():
            now=self._iso(); self.db.execute("UPDATE bridge_state SET enabled=?,updated_at=? WHERE singleton=1",(int(enabled),now))
            if consumed_ref: self.db.execute("INSERT OR IGNORE INTO consumed_mail VALUES(?,?)",(consumed_ref,now))
    def session_health(self) -> SessionHealth:
        r=self.db.execute("SELECT * FROM session_health WHERE singleton=1").fetchone()
        return SessionHealth(bool(r["valid"]),bool(r["notified"]),datetime.fromisoformat(r["updated_at"]))
    def set_session(self, valid: bool, notified: bool = False):
        self.db.execute("UPDATE session_health SET valid=?,notified=?,updated_at=? WHERE singleton=1",(int(valid),int(notified),self._iso()))
    def mark_session_notified(self):
        self.db.execute("UPDATE session_health SET notified=1,updated_at=? WHERE singleton=1",(self._iso(),))

    def backoff(self, scope: str) -> BackoffDecision | None:
        r=self.db.execute("SELECT * FROM runtime_backoff WHERE scope=?",(scope,)).fetchone()
        return BackoffDecision(datetime.fromisoformat(r["not_before"]),r["failures"]) if r else None
    def set_backoff(self, scope: str, decision: BackoffDecision):
        self.db.execute("INSERT INTO runtime_backoff VALUES(?,?,?,?) ON CONFLICT(scope) DO UPDATE SET not_before=excluded.not_before,failures=excluded.failures,updated_at=excluded.updated_at",
                        (scope,self._iso(decision.not_before),decision.failures,self._iso()))
    def clear_backoff(self, scope: str): self.db.execute("DELETE FROM runtime_backoff WHERE scope=?",(scope,))
    def clear_tg_backoff(self): self.db.execute("DELETE FROM runtime_backoff WHERE scope LIKE 'tg:%'")
    def queue_notice(self, kind: str, subject: str, body: str):
        self.db.execute("INSERT OR REPLACE INTO pending_notice VALUES(?,?,?,?)",(kind,subject,body,self._iso()))
    def pending_notices(self): return self.db.execute("SELECT kind,subject,body FROM pending_notice ORDER BY created_at").fetchall()
    def delete_notice(self, kind: str): self.db.execute("DELETE FROM pending_notice WHERE kind=?",(kind,))

    def purge_retention(self, *, retention_seconds: int, max_ledger: int, max_consumed: int,
                        max_echo: int, echo_retention_seconds: int, now: datetime | None=None):
        epoch=(now or datetime.now(timezone.utc)).timestamp()
        cut=datetime.fromtimestamp(epoch-retention_seconds,timezone.utc).isoformat()
        echo_cut=datetime.fromtimestamp(epoch-echo_retention_seconds,timezone.utc).isoformat()
        with self.transaction():
            self.db.execute("DELETE FROM mail_ledger WHERE delivered_at<?",(cut,)); self.db.execute("DELETE FROM consumed_mail WHERE consumed_at<?",(cut,))
            self.db.execute("DELETE FROM posted_echo WHERE posted_at<?",(echo_cut,))
            for table,col,limit in (("mail_ledger","delivered_at",max_ledger),("consumed_mail","consumed_at",max_consumed),("posted_echo","posted_at",max_echo)):
                self.db.execute(f"DELETE FROM {table} WHERE rowid IN (SELECT rowid FROM {table} ORDER BY {col} DESC LIMIT -1 OFFSET ?)",(limit,))
