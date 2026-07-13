import pytest
from mailtg_bridge.config import Settings
from mailtg_bridge.domain import BotPolicy
from mailtg_bridge.errors import ConfigError
from tests.helpers import settings_env as env

def test_settings_defaults(tmp_path):
    s=Settings.from_env(environ=env(tmp_path)); assert s.tg_fetch_limit==100 and s.whitelist==("@public","-1001:2")
    # v0.1-compatible defaults: bots bridged as before, sent-copy on
    assert s.bot_policy is BotPolicy.ALL and s.bot_list==() and s.save_sent_copy is True and s.sent_folder=="Sent"

def test_bot_and_sent_settings_parse(tmp_path):
    e=env(tmp_path); e['BOT_POLICY']='selected'; e['BOT_LIST_JSON']='["@GoodBot"]'; e['SAVE_SENT_COPY']='false'; e['SENT_FOLDER']='Sent Items'
    s=Settings.from_env(environ=e)
    assert s.bot_policy is BotPolicy.SELECTED and s.bot_list==('@goodbot',) and s.save_sent_copy is False and s.sent_folder=='Sent Items'
    e2=env(tmp_path); e2['BOT_POLICY']='bogus'
    with pytest.raises(ConfigError): Settings.from_env(environ=e2)

def test_plaintext_and_relative_or_bad_limits_rejected(tmp_path):
    e=env(tmp_path); e["B_IMAP_SECURITY"]="plain"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
    e=env(tmp_path); e["ATTACHMENT_THRESHOLD_BYTES"]="100"; e["EMAIL_SIZE_LIMIT_BYTES"]="100"
    with pytest.raises(ConfigError): Settings.from_env(environ=e)
