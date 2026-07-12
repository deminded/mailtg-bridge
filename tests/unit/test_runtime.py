import json, multiprocessing
import pytest
from mailtg_bridge.errors import AlreadyRunning
from mailtg_bridge.locking import LifetimeLock
from mailtg_bridge.logging import JsonFormatter, redact
import logging

def test_lock_exclusive_and_private(tmp_path):
    path=tmp_path/'run'/'lock'
    with LifetimeLock(path):
        with pytest.raises(AlreadyRunning): LifetimeLock(path).acquire()
    assert path.stat().st_mode & 0o777 == 0o600
def test_log_redaction_and_json():
    assert 'secret' not in redact('password=secret token: abc')
    r=logging.LogRecord('x',20,'',0,'api_hash=hidden',(),None); value=JsonFormatter().format(r)
    assert 'hidden' not in value and json.loads(value)['level']=='INFO'
