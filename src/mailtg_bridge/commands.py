from __future__ import annotations
import hmac, re
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class Command:
    enabled: bool

_RE=re.compile(r"^MAILTG\s+(ON|OFF)(?:\s+([^\s]+))?$",re.I)

def parse_command(subject: str, body: str, required_token: str="") -> Command | None:
    candidates=[]
    if subject.strip(): candidates.append(subject.strip())
    lines=[x.strip() for x in body.splitlines() if x.strip()]
    if lines: candidates.append(lines[0])
    for text in candidates:
        m=_RE.fullmatch(text)
        if not m: continue
        supplied=m.group(2) or ""
        if required_token and not hmac.compare_digest(supplied.encode(),required_token.encode()): return None
        if not required_token and supplied: return None
        return Command(m.group(1).upper()=="ON")
    return None
