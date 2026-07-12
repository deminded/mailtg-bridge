from mailtg_bridge.errors import FloodWait, PeerNotFound, SessionInvalid, Transient
from mailtg_bridge.telegram import classify_error, parse_source

def error(name,**attrs): return type(name,(Exception,),attrs)()
def test_error_mapping_and_source():
    assert isinstance(classify_error(error('FloodWaitError',seconds=42)),FloodWait)
    assert isinstance(classify_error(error('SessionRevokedError')),SessionInvalid)
    assert isinstance(classify_error(error('UsernameInvalidError')),PeerNotFound)
    assert isinstance(classify_error(OSError()),Transient)
    assert parse_source('-1001:42')==('-1001',42)
