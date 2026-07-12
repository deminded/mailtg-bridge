from __future__ import annotations
import hashlib, json, logging, re

SENSITIVE=re.compile(r"(?i)(password|token|api[_ -]?hash|authorization|session)(\s*[:=]\s*)([^\s,;}]+)")
def redact(value):
    text=str(value).replace("\r"," ").replace("\n"," ")
    return SENSITIVE.sub(lambda m:m.group(1)+m.group(2)+"[REDACTED]",text)
def dialog_hash(dialog_id): return hashlib.sha256(dialog_id.encode()).hexdigest()[:12]
class JsonFormatter(logging.Formatter):
    def format(self,record):
        data={"level":record.levelname,"event":redact(record.getMessage()),"logger":record.name}
        for key in ("operation","count","duration_ms","error_class","next_retry"):
            if hasattr(record,key): data[key]=redact(getattr(record,key))
        return json.dumps(data,ensure_ascii=False,separators=(",",":"))
def configure(level="INFO"):
    handler=logging.StreamHandler(); handler.setFormatter(JsonFormatter()); root=logging.getLogger(); root.handlers[:]=[handler]; root.setLevel(level)
