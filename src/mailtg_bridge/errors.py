"""Stable error taxonomy exposed by external adapters."""

class BridgeError(Exception):
    pass

class ConfigError(BridgeError):
    pass

class Transient(BridgeError):
    pass

class FloodWait(Transient):
    def __init__(self, wait_seconds: int):
        self.wait_seconds = max(0, int(wait_seconds))
        super().__init__(f"Telegram rate limit ({self.wait_seconds}s)")

class SessionInvalid(BridgeError):
    pass

class PeerNotFound(BridgeError):
    pass

class MediaUnavailable(BridgeError):
    pass

class MailAuthError(BridgeError):
    pass

class MailSizeRejected(BridgeError):
    pass

class AlreadyRunning(BridgeError):
    pass
