import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from composer import VNI, convert_text, create_composer, preview
from settings import SettingsStore, validate
from runtime_status import RuntimeStatus


class FeatureTests(unittest.TestCase):
    def test_vni_words_and_literal_telex_keys(self):
        words = {"tie61ng": "tiếng", "Vie65t": "Việt", "To6i": "Tôi", "d9a8ng": "đăng",
                 "d9uo72ng": "đường", "nguoi72": "người", "D9O62NG": "ĐỒNG", "hoa2": "hòa",
                 "quye62n": "quyền", "thu3y": "thủy", "hello": "hello", "as": "as",
                 "123": "123", "a11": "a1", "a10": "a", "a66": "a6", "d99": "d9",
                 "uo77": "uo7", "a8": "ă", "u7": "ư", "o7": "ơ"}
        for raw, expected in words.items():
            with self.subTest(raw=raw):
                composer = VNI()
                for char in raw:
                    composer.feed(char)
                self.assertEqual(composer.text, expected)
                self.assertEqual(composer.raw, raw)

    def test_vni_all_vowels_tones_and_case(self):
        import unicodedata
        for raw, base in {"a": "a", "a8": "ă", "a6": "â", "e": "e", "e6": "ê", "i": "i", "o": "o", "o6": "ô", "o7": "ơ", "u": "u", "u7": "ư", "y": "y"}.items():
            for key, tone in zip("12345", ("\u0301", "\u0300", "\u0309", "\u0303", "\u0323")):
                for upper in (False, True):
                    typed = (raw + key).upper() if upper else raw + key
                    settings = validate({"input_method": "vni"})
                    self.assertEqual(preview(typed, settings), unicodedata.normalize("NFC", (base.upper() if upper else base) + tone))

    def test_tone_styles_and_backspace(self):
        for method, raw in (("telex", "hoaf"), ("vni", "hoa2")):
            self.assertEqual(preview(raw, validate({"input_method": method})), "hòa")
            settings = validate({"input_method": method, "modern_tone": True})
            self.assertEqual(preview(raw, settings), "hoà")
            composer = create_composer(settings)
            for char in raw:
                composer.feed(char)
            self.assertEqual(composer.backspace(), "ho")
            self.assertEqual(composer.raw, "ho")

    def test_macro_requires_boundary_and_exact_case(self):
        settings = validate({"macros_enabled": True, "macros": {"btw": "nhân tiện", "a1": "mục một"}})
        self.assertEqual(preview("btw", settings), "btw")
        self.assertEqual(preview("btw, a1! BTW ", settings), "nhân tiện, mục một! BTW ")
        self.assertEqual(preview("btwé", settings), "btwé")

    def test_text_conversion(self):
        self.assertEqual(convert_text("Đường về HÀ NỘI", "strip"), "Duong ve HA NOI")
        self.assertEqual(convert_text("Tiếng Việt", "upper"), "TIẾNG VIỆT")
        self.assertEqual(convert_text("TIẾNG VIỆT", "lower"), "tiếng việt")


class SettingsTests(unittest.TestCase):
    def test_runtime_diagnostics_keep_last_typing_result_after_focus_changes(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", XDG_RUNTIME_DIR=directory):
            status = RuntimeStatus()
            status.report("preedit", "no-surrounding-support", 9)
            status.report("ready", "", 41)
            path = Path(directory) / "bo-go-viet-status.json"
            value = json.loads(path.read_text())
            self.assertEqual(value["mode"], "ready")
            self.assertEqual(value["last_typing"], dict(mode="preedit", reason="no-surrounding-support", capabilities=9))
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_missing_runtime_directory_cannot_interrupt_typing(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict("os.environ", XDG_RUNTIME_DIR=str(Path(directory)/"missing")):
            RuntimeStatus().report("forward", "", 9)

    def test_atomic_save_refresh_and_independent_updates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config/settings.json"
            first, second = SettingsStore(path), SettingsStore(path)
            first.update(input_method="vni")
            second.update(modern_tone=True)
            self.assertTrue(first.refresh())
            self.assertEqual(first.value["input_method"], "vni")
            self.assertTrue(first.value["modern_tone"])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_invalid_configuration_preserves_last_good_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            store = SettingsStore(path)
            store.update(input_method="vni")
            for invalid in ("{", json.dumps({"enabled": "false"}), json.dumps({"macros": {"a": ""}})):
                path.write_text(invalid)
                self.assertFalse(store.refresh())
                self.assertTrue(store.error)
                self.assertEqual(store.value["input_method"], "vni")
                with self.assertRaises(ValueError):
                    store.update(enabled=False)

    def test_import_validation(self):
        for value in ([], {"input_method": "auto"}, {"typing_mode": "hooks"}, {"underline": "false"}, {"enabled": 1}, {"macros": {"có": "yes"}}, {"macros": {"a": "\x00"}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate(value)


if __name__ == "__main__":
    unittest.main()
