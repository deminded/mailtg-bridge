from __future__ import annotations
import getpass
from .config import Settings
from .state import SQLiteStore
from .telegram import authorize_interactive

async def run_setup(settings: Settings, reauthorize: bool=False):
    phone=input("Telegram phone: ").strip()
    me=await authorize_interactive(settings,phone,lambda: input("Telegram code: ").strip(),lambda: getpass.getpass("2FA password: "),reauthorize)
    with SQLiteStore(settings.state_db_path) as store:
        store.set_session(True,False); store.clear_tg_backoff()
    return me
