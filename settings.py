"""Validated, atomic per-user preferences shared by the UI and IBus."""
import json
import os
from pathlib import Path
import tempfile

VERSION = "0.3.2"
DEFAULTS = {
    "enabled": True,
    "input_method": "telex",
    "modern_tone": False,
    "typing_mode": "preedit",
    "underline": False,
    "macros_enabled": False,
    "macros": {"btw": "nhân tiện", "dc": "được", "ko": "không"},
}


def validate(value):
    if not isinstance(value, dict):
        raise ValueError("Cấu hình phải là một đối tượng JSON.")
    result = dict(DEFAULTS, macros=dict(DEFAULTS["macros"]))
    for key in ("enabled", "modern_tone", "macros_enabled", "underline"):
        if key in value:
            if type(value[key]) is not bool:
                raise ValueError(f"{key} phải là bật hoặc tắt.")
            result[key] = value[key]
    if "typing_mode" in value:
        if value["typing_mode"] not in ("preedit", "direct", "forward"):
            raise ValueError("Cách nhập phải là soạn từ, nhập trực tiếp hoặc trực tiếp qua phím.")
        result["typing_mode"] = value["typing_mode"]
    if "input_method" in value:
        if value["input_method"] not in ("telex", "vni"):
            raise ValueError("Kiểu gõ phải là Telex hoặc VNI.")
        result["input_method"] = value["input_method"]
    if "macros" in value:
        macros = value["macros"]
        if not isinstance(macros, dict) or len(macros) > 1000:
            raise ValueError("Danh sách gõ tắt chứa tối đa 1.000 mục.")
        for key, expansion in macros.items():
            if not isinstance(key, str) or not 1 <= len(key) <= 32 or not key.isascii() or not key.isalnum():
                raise ValueError("Từ viết tắt cần 1–32 chữ cái hoặc chữ số không dấu.")
            if not isinstance(expansion, str) or not expansion.strip() or len(expansion) > 4096 or "\x00" in expansion:
                raise ValueError("Nội dung thay thế cần 1–4.096 ký tự, không chứa NUL.")
        result["macros"] = dict(macros)
    return result


class SettingsStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "bo-go-viet/settings.json"
        self.error = ""
        self.signature = None
        self.value = validate({})
        self.reload()

    def _signature(self):
        try:
            stat = self.path.stat()
            return stat.st_mtime_ns, stat.st_size, stat.st_ino
        except FileNotFoundError:
            return None

    def reload(self):
        try:
            signature = self._signature()
            if signature is None:
                value = validate({})
            else:
                if self.path.stat().st_size > 5_000_000:
                    raise ValueError("Tệp cấu hình quá lớn.")
                value = validate(json.loads(self.path.read_text(encoding="utf-8")))
            self.signature, self.value, self.error = signature, value, ""
            return True
        except (OSError, ValueError, UnicodeError) as exc:
            self.error = str(exc)
            return False

    def refresh(self):
        try:
            changed = self._signature() != self.signature
        except OSError as exc:
            self.error = str(exc)
            return False
        return self.reload() if changed else False

    def save(self, value):
        value = validate(value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump(value, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)
        self.reload()

    def update(self, **changes):
        # Preserve settings saved by another process since this window opened.
        if not self.reload():
            raise ValueError("Không thể đọc cấu hình hiện tại: " + self.error)
        self.save(dict(self.value, **changes))
