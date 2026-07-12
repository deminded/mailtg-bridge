from datetime import datetime, timezone
import pytest
from mailtg_bridge.domain import DialogRef, SentMail, SourceType
from mailtg_bridge.state import SQLiteStore

def dialog(): return DialogRef("-1001",SourceType.CHANNEL,source_tag="x",whitelisted=True)

def test_cursor_monotonic_and_atomic_delivery(tmp_path):
    with SQLiteStore(tmp_path/"state.db") as s:
        d=dialog(); assert s.get_cursor(d).last_id==0
        s.advance_cursor(d,10); s.advance_cursor(d,3); assert s.get_cursor(d).last_id==10
        s.commit_delivery(d,[SentMail("<m@x>",d.dialog_id,d.source_type)],20)
        assert s.get_cursor(d).last_id==20 and s.ledger_dialog(["<m@x>"])==d.dialog_id
        with pytest.raises(Exception): s.commit_delivery(d,[SentMail("<m@x>",d.dialog_id,d.source_type)],30)
        assert s.get_cursor(d).last_id==20

def test_action_before_consume_and_singletons(tmp_path):
    with SQLiteStore(tmp_path/"s.db") as s:
        assert not s.is_consumed("uid:1")
        s.commit_reply("uid:1","d",7)
        assert s.is_consumed("uid:1") and s.is_echo("d",7)
        s.set_bridge_enabled(False,"uid:2")
        assert not s.bridge_state().enabled and s.is_consumed("uid:2")

def test_permissions(tmp_path):
    p=tmp_path/"private"/"s.db"
    with SQLiteStore(p): pass
    assert p.stat().st_mode & 0o777 == 0o600
    assert p.parent.stat().st_mode & 0o777 == 0o700
