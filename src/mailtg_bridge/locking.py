from __future__ import annotations
import fcntl, os
from pathlib import Path
from .errors import AlreadyRunning

class LifetimeLock:
    def __init__(self,path): self.path=Path(path); self.fd=None
    def acquire(self):
        self.path.parent.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(self.path.parent,0o700)
        self.fd=os.open(self.path,os.O_CREAT|os.O_RDWR,0o600); os.fchmod(self.fd,0o600)
        try: fcntl.flock(self.fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as exc: os.close(self.fd); self.fd=None; raise AlreadyRunning("mailtg-bridge is already running") from exc
        os.ftruncate(self.fd,0); os.write(self.fd,str(os.getpid()).encode()); return self
    def release(self):
        if self.fd is not None: fcntl.flock(self.fd,fcntl.LOCK_UN); os.close(self.fd); self.fd=None
    def __enter__(self): return self.acquire()
    def __exit__(self,*_): self.release()
