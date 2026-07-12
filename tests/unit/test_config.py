import pytest
from mailtg_bridge.config import Settings
from mailtg_bridge.errors import ConfigError
from tests.helpers import settings_env as env

def test_settings_defaults(tmp_path):
    s=Settings.from_env(environ=env(tmp_path)); assert s.tg_fetch_limit==100 and s.whitelist==("@public","-1001:2")

def test_plaintext_and_relative_or_bad_limits_rejected(tmp_path):
    e=env(tmp_path); e["B_IMAP_SECURITY"]="plain"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
    e=env(tmp_path); e["ATTACHMENT_THRESHOLD_BYTES"]="100"; e["EMAIL_SIZE_LIMIT_BYTES"]="100"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
