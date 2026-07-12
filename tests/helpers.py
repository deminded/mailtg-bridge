def settings_env(tmp_path):
    return dict(TG_API_ID="1",TG_API_HASH="secret",TG_SESSION_PATH=str(tmp_path/"tg"),B_ADDRESS="b@x.io",
      B_USERNAME="b",B_PASSWORD="pw",B_IMAP_HOST="imap.x",B_SMTP_HOST="smtp.x",U_ADDRESS="u@x.io",
      STATE_DB_PATH=str(tmp_path/"s.db"),LOCK_PATH=str(tmp_path/"l"),TEMP_DIR=str(tmp_path/"tmp"),
      WHITELIST_JSON='["@public","-1001:2"]')
