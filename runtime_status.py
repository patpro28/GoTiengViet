"""Content-free runtime diagnostics; never includes surrounding text or keys."""
import json
import os
from pathlib import Path
import tempfile
from settings import VERSION


def status_path():
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    return Path(runtime) / "bo-go-viet-status.json" if runtime else None


class RuntimeStatus:
    def __init__(self):
        self.last = None
        self.last_typing = None

    def report(self, mode, reason, capabilities):
        path = status_path()
        if mode in ("preedit", "direct", "forward"):
            self.last_typing = dict(mode=mode, reason=reason, capabilities=int(capabilities))
        value = dict(version=VERSION, pid=os.getpid(), mode=mode, reason=reason, capabilities=int(capabilities), last_typing=self.last_typing)
        if path is None or value == self.last:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(value, stream)
            os.replace(temporary, path)
            self.last = value
        except OSError:
            pass
        finally:
            if temporary is not None:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
