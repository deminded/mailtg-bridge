from __future__ import annotations
import argparse, asyncio, os, signal, sys
from pathlib import Path
from .config import Settings, assert_private
from .errors import AlreadyRunning, BridgeError, ConfigError
from .locking import LifetimeLock
from .logging import configure
from .mail_in import ImapMailbox
from .mail_out import EmailComposer, SmtpMailer
from .orchestrator import BridgeService
from .setup import run_setup
from .state import SQLiteStore
from .telegram import TelethonGateway

def parser():
    p=argparse.ArgumentParser(prog="mailtg-bridge"); p.add_argument("--env",default=os.environ.get("MAILTG_ENV"))
    sub=p.add_subparsers(dest="command",required=True); sub.add_parser("run")
    o=sub.add_parser("once"); o.add_argument("--kind",choices=("all","inbound","mailbox"),default="all")
    x=sub.add_parser("setup"); x.add_argument("--reauthorize",action="store_true")
    sub.add_parser("check-config"); sub.add_parser("purge"); return p
def load(args):
    if args.env: assert_private(Path(args.env))
    s=Settings.from_env(args.env); s.temp_dir.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(s.temp_dir,0o700)
    return s
async def execute(args,s):
    if args.command=="setup": await run_setup(s,args.reauthorize); return 0
    with SQLiteStore(s.state_db_path) as store:
        if args.command=="purge": store.purge_retention(retention_seconds=s.retention_seconds,max_ledger=s.retention_max_ledger,max_consumed=s.retention_max_consumed,max_echo=s.retention_max_echo,echo_retention_seconds=s.echo_retention_seconds); return 0
        tg=TelethonGateway(s); await tg.connect()
        try:
            svc=BridgeService(s,store,tg,ImapMailbox(s),SmtpMailer(s),EmailComposer(s))
            if args.command=="once": await svc.run_once(args.kind)
            else:
                loop=asyncio.get_running_loop()
                for sig in (signal.SIGINT,signal.SIGTERM): loop.add_signal_handler(sig,svc.stop)
                await svc.run()
        finally: await tg.close()
    return 0
def main(argv=None):
    args=parser().parse_args(argv)
    try:
        s=load(args); configure(s.log_level)
        if args.command=="check-config":
            assert_private(s.state_db_path); assert_private(s.state_db_path.parent,True); print("configuration valid"); return 0
        with LifetimeLock(s.lock_path): return asyncio.run(execute(args,s))
    except AlreadyRunning as exc: print(str(exc),file=sys.stderr); return 73
    except (BridgeError,OSError,ValueError) as exc: print(f"{type(exc).__name__}: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
