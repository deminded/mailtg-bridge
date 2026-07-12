import pytest
from mailtg_bridge.config import Settings
from mailtg_bridge.errors import ConfigError

def env(tmp_path):
    return dict(TG_API_ID="1",TG_API_HASH="secret",TG_SESSION_PATH=str(tmp_path/"tg"),B_ADDRESS="b@x.io",
      B_USERNAME="b",B_PASSWORD="pw",B_IMAP_HOST="imap.x",B_SMTP_HOST="smtp.x",U_ADDRESS="u@x.io",
      STATE_DB_PATH=str(tmp_path/"s.db"),LOCK_PATH=str(tmp_path/"l"),TEMP_DIR=str(tmp_path/"tmp"),
      WHITELIST_JSON='["@public","-1001:2"]')

def test_settings_defaults(tmp_path):
    s=Settings.from_env(environ=env(tmp_path)); assert s.tg_fetch_limit==100 and s.whitelist==("@public","-1001:2")

def test_plaintext_and_relative_or_bad_limits_rejected(tmp_path):
    e=env(tmp_path); e["B_IMAP_SECURITY"]="plain"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
    e=env(tmp_path); e["ATTACHMENT_THRESHOLD_BYTES"]="100"; e["EMAIL_SIZE_LIMIT_BYTES"]="100"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
