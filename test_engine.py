"""Exercise the actual engine callbacks without opening a desktop D-Bus."""
import unittest
import tempfile
from pathlib import Path
from engine import IBus, VietEngine
from telex import Telex
from settings import SettingsStore
from direct import DirectBuffer
from unittest.mock import Mock
from collections import deque


class StubEngine:
    vietnamese = True

    def __init__(self):
        self.vietnamese = True
        self.composer = Telex()
        self.directory = tempfile.TemporaryDirectory()
        self.settings = SettingsStore(Path(self.directory.name) / "settings.json")
        self.private = False
        self.committed = []
        self.preedit = ""
        self.preedit_attributes = None
        self.capabilities = 0
        self.direct = DirectBuffer()
        self.presentation = None
        self.document = ""
        self.cursor = 0
        self.anchor = 0
        self.deletions = []
        self.surrounding_reads = 0
        self.snapshot_override = None
        self.runtime_status = Mock()
        self.forward_text = ""
        self.forwarded = []
        self.forward_pending = None
        self.forward_generation = 0
        self.forward_queue = deque()
        self.scheduled = {}
        self.next_source = 0

    def update_preedit_text(self, text, cursor, visible):
        self.preedit = text.get_text()
        self.preedit_attributes = text.get_attributes()

    def commit_text(self, text):
        self.committed.append(text.get_text())
        start, end = sorted((self.cursor, self.anchor))
        self.document = self.document[:start] + text.get_text() + self.document[end:]
        self.cursor = self.anchor = start + len(text.get_text())

    def get_surrounding_text(self):
        self.surrounding_reads += 1
        if self.snapshot_override is not None:
            text, cursor, anchor = self.snapshot_override
            return IBus.Text.new_from_string(text), cursor, anchor
        return IBus.Text.new_from_string(self.document), self.cursor, self.anchor

    def delete_surrounding_text(self, offset, count):
        self.deletions.append((offset, count))
        start = self.cursor + offset
        self.document = self.document[:start] + self.document[start + count:]
        self.cursor = self.anchor = start

    def forward_key_event(self, keyval, keycode, state):
        self.forwarded.append((keyval, keycode, state))
        if keyval == IBus.KEY_BackSpace and not state & IBus.ModifierType.RELEASE_MASK:
            self.document = self.document[:self.cursor - 1] + self.document[self.cursor:]
            self.cursor = self.anchor = self.cursor - 1
        elif not state & (IBus.ModifierType.RELEASE_MASK | IBus.ModifierType.CONTROL_MASK):
            char = IBus.keyval_to_unicode(keyval)
            if char and char.isprintable():
                self.document = self.document[:self.cursor] + char + self.document[self.cursor:]
                self.cursor = self.anchor = self.cursor + len(char)

    def _schedule_forward(self, delay, callback):
        self.next_source += 1
        self.scheduled[self.next_source] = callback
        return self.next_source

    def _remove_forward_source(self, source):
        self.scheduled.pop(source, None)

    def flush_forward(self):
        while self.scheduled:
            source = next(iter(self.scheduled))
            self.scheduled.pop(source)()

    def register_properties(self, properties):
        pass


for name in ("_report", "_sync_settings", "_surrounding", "_prepare_direct", "_write_direct", "_write_forward", "_finish_forward", "_cancel_forward", "_process_key_event", "_show_preedit", "_update", "_clear", "_commit", "_properties", "_toggle", "do_process_key_event",
             "do_focus_in", "do_focus_out", "do_reset", "do_disable", "do_set_content_type", "do_set_capabilities", "do_enable"):
    setattr(StubEngine, name, getattr(VietEngine, name))


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.engine = StubEngine()
        self.addCleanup(self.engine.directory.cleanup)

    def key(self, value, state=0):
        keyval = ord(value) if isinstance(value, str) else value
        handled = self.engine.do_process_key_event(keyval, 0, state)
        if not handled and keyval == IBus.KEY_BackSpace and self.engine.cursor:
            self.engine.document = self.engine.document[:self.engine.cursor - 1] + self.engine.document[self.engine.cursor:]
            self.engine.cursor = self.engine.anchor = self.engine.cursor - 1
        self.engine.flush_forward()
        return handled

    def type_word(self, word):
        for char in word:
            self.assertTrue(self.key(char))

    def test_preedit_and_commit_at_boundary(self):
        self.type_word("tieengs")
        self.assertEqual(self.engine.preedit, "tiếng")
        self.assertFalse(self.key(" "))
        self.assertEqual(self.engine.committed, ["tiếng"])
        self.assertEqual(self.engine.preedit, "")

    def test_backspace(self):
        self.type_word("Vieetj")
        self.assertTrue(self.key(IBus.KEY_BackSpace))
        self.assertEqual(self.engine.preedit, "Việ")
        for _ in range(3):
            self.key(IBus.KEY_BackSpace)
        self.assertFalse(self.key(IBus.KEY_BackSpace))

    def test_escape_restores_raw_keys(self):
        self.type_word("book")
        self.assertEqual(self.engine.preedit, "bôk")
        self.assertTrue(self.key(IBus.KEY_Escape))
        self.assertEqual(self.engine.committed, ["book"])

    def test_english_toggle(self):
        self.type_word("tieengs")
        mask = IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK
        self.assertTrue(self.key(" ", mask))
        self.assertEqual(self.engine.committed, ["tiếng"])
        self.assertFalse(self.key("a"))
        self.assertTrue(self.key(" ", mask))
        self.assertTrue(self.key("a"))

    def test_shortcuts_commit_and_pass_through(self):
        self.type_word("Vieetj")
        self.assertFalse(self.key("c", IBus.ModifierType.CONTROL_MASK))
        self.assertEqual(self.engine.committed, ["Việt"])

    def test_release_does_not_type_twice(self):
        self.key("a")
        self.assertFalse(self.key("a", IBus.ModifierType.RELEASE_MASK))
        self.assertEqual(self.engine.preedit, "a")

    def test_modifier_alone_keeps_preedit(self):
        self.type_word("tieengs")
        self.assertFalse(self.key(IBus.KEY_Shift_L))
        self.assertEqual(self.engine.preedit, "tiếng")
        self.assertEqual(self.engine.committed, [])

    def test_password_pin_and_private_hint(self):
        for purpose, hints in [(IBus.InputPurpose.PASSWORD, 0), (IBus.InputPurpose.PIN, 0),
                               (IBus.InputPurpose.FREE_FORM, IBus.InputHints.PRIVATE)]:
            self.engine.do_set_content_type(IBus.InputPurpose.FREE_FORM, 0)
            self.key("a")
            self.engine.do_set_content_type(purpose, hints)
            self.assertEqual(self.engine.preedit, "")
            self.assertFalse(self.key("s"))
            self.assertFalse(self.key(" ", IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK))
            self.assertEqual(self.engine.committed, [])

    def test_focus_out_and_disable_commit_once(self):
        self.type_word("ddawng")
        self.engine.do_focus_out()
        self.engine.do_disable()
        self.assertEqual(self.engine.committed, ["đăng"])

    def test_reset_clears_without_committing(self):
        self.type_word("tieengs")
        self.engine.do_reset()
        self.assertEqual(self.engine.committed, [])
        self.assertEqual(self.engine.preedit, "")

    def test_composition_has_bounded_length(self):
        for _ in range(200):
            self.key("b")
        self.assertEqual(self.engine.committed, ["b" * 128])
        self.assertEqual(self.engine.preedit, "b" * 72)

    def test_live_settings_commit_pending_word_and_switch_to_vni(self):
        self.type_word("tieengs")
        other = SettingsStore(self.engine.settings.path)
        other.update(input_method="vni")
        self.type_word("Vie65t")
        self.assertEqual(self.engine.committed, ["tiếng"])
        self.assertEqual(self.engine.preedit, "Việt")

    def test_macro_expansion_on_boundary_but_not_shortcut_or_password(self):
        self.engine.settings.update(macros_enabled=True, macros={"btw": "nhân tiện", "a1": "mục một"})
        self.type_word("btw")
        self.key(" ")
        self.assertEqual(self.engine.committed, ["nhân tiện"])
        self.type_word("btw")
        self.key("c", IBus.ModifierType.CONTROL_MASK)
        self.assertEqual(self.engine.committed[-1], "btw")
        self.type_word("a1")
        self.key(IBus.KEY_Return)
        self.assertEqual(self.engine.committed[-1], "mục một")
        self.type_word("btw")
        self.assertFalse(self.key(IBus.KEY_Delete))
        self.assertEqual(self.engine.committed[-1], "btw")
        self.engine.do_set_content_type(IBus.InputPurpose.PASSWORD, 0)
        self.assertFalse(self.key("b"))

    def test_live_disable_does_not_swallow_next_key(self):
        self.type_word("a")
        SettingsStore(self.engine.settings.path).update(enabled=False)
        self.assertFalse(self.key("s"))
        self.assertEqual(self.engine.committed, ["a"])

    def enable_direct(self, prefix=""):
        self.engine.document = prefix
        self.engine.cursor = self.engine.anchor = len(prefix)
        self.engine.settings.update(typing_mode="direct")
        self.engine.do_set_capabilities(IBus.Capabilite.SURROUNDING_TEXT)

    def test_preedit_sends_explicit_underline_setting(self):
        for underline in (False, True):
            self.engine.settings.update(underline=underline)
            self.key("a")
            attribute = self.engine.preedit_attributes.get(0)
            self.assertEqual(attribute.get_attr_type(), IBus.AttrType.UNDERLINE)
            self.assertEqual(attribute.get_value(), IBus.AttrUnderline.SINGLE if underline else IBus.AttrUnderline.NONE)
            self.engine.do_reset()

    def test_direct_delivers_every_key_without_preedit_or_duplicate_commit(self):
        self.enable_direct("Có sẵn: ")
        for char, expected in zip("tieengs", ("t", "ti", "tie", "tiê", "tiên", "tiêng", "tiếng")):
            self.key(char)
            self.assertEqual(self.engine.document, "Có sẵn: " + expected)
            self.assertEqual(self.engine.preedit, "")
        before = list(self.engine.committed)
        self.assertFalse(self.key(" "))
        self.engine.do_focus_out()
        self.assertEqual(self.engine.document, "Có sẵn: tiếng")
        self.assertEqual(self.engine.committed, before)

    def test_direct_backspace_escape_macro_and_reset(self):
        self.enable_direct()
        self.type_word("Vieetj")
        self.key(IBus.KEY_BackSpace)
        self.assertEqual(self.engine.document, "Việ")
        self.engine.do_reset()
        self.assertEqual(self.engine.document, "Việ")
        self.type_word("book")
        self.assertTrue(self.key(IBus.KEY_Escape))
        self.assertEqual(self.engine.document, "Việbook")
        self.engine.settings.update(macros_enabled=True, macros={"btw": "nhân tiện"})
        self.type_word("btw")
        self.key(" ")
        self.assertEqual(self.engine.document, "Việbooknhân tiện")

    def test_direct_abandons_ownership_after_cursor_move_or_selection(self):
        for selection in (False, True):
            self.engine.do_reset()
            self.enable_direct("Nội dung: ")
            self.type_word("tieengs")
            deletions = list(self.engine.deletions)
            self.engine.cursor = 0
            self.engine.anchor = 3 if selection else 0
            self.key("a")
            self.assertEqual(self.engine.document, "Nội dung: tiếng")
            self.assertEqual(self.engine.deletions, deletions)
            self.assertEqual(self.engine.preedit, "a")

    def test_direct_falls_back_without_surrounding_support_and_skips_password(self):
        self.enable_direct()
        self.engine.capabilities = 0
        self.type_word("tieengs")
        self.assertEqual(self.engine.preedit, "tiếng")
        self.assertEqual(self.engine.document, "")
        self.assertEqual(self.engine.surrounding_reads, 0)
        self.engine.do_set_content_type(IBus.InputPurpose.PASSWORD, 0)
        self.engine.capabilities = IBus.Capabilite.SURROUNDING_TEXT
        self.assertFalse(self.key("a"))
        self.assertEqual(self.engine.surrounding_reads, 0)

    def test_direct_stale_acknowledgement_never_deletes_or_repeats_prior_text(self):
        self.enable_direct()
        self.key("a")
        self.assertEqual(self.engine.document, "a")
        self.engine.snapshot_override = ("", 0, 0)
        self.key("s")
        self.assertEqual(self.engine.document, "a")
        self.assertEqual(self.engine.preedit, "s")
        self.assertEqual(self.engine.deletions, [])

    def test_forward_mode_no_surrounding_no_visible_preedit(self):
        self.engine.settings.update(typing_mode="forward")
        self.engine.document = "Có sẵn: "
        self.engine.cursor = self.engine.anchor = len(self.engine.document)
        for char, expected in zip("Phamj", ("P", "Ph", "Pha", "Pham", "Phạm")):
            self.key(char)
            self.assertEqual(self.engine.document, "Có sẵn: " + expected)
            self.assertEqual(self.engine.preedit, "")
        self.assertEqual(self.engine.surrounding_reads, 0)
        self.assertEqual(len(self.engine.forwarded), 4)
        before = list(self.engine.committed)
        self.key(" ")
        self.engine.do_focus_out()
        self.assertEqual(self.engine.committed, before)

    def test_forward_backspace_escape_macro_and_toggle(self):
        self.engine.settings.update(typing_mode="forward", macros_enabled=True, macros={"btw": "nhân tiện"})
        self.type_word("Vieetj")
        self.key(IBus.KEY_BackSpace)
        self.assertEqual(self.engine.document, "Việ")
        self.engine.do_reset()
        self.type_word("book")
        self.key(IBus.KEY_Escape)
        self.assertEqual(self.engine.document, "Việbook")
        self.type_word("btw")
        self.key(" ")
        self.assertEqual(self.engine.document, "Việbooknhân tiện")
        self.key(" ", IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.SHIFT_MASK)
        self.assertEqual(self.engine.document, "Việbooknhân tiện")
        self.assertFalse(self.key("a"))

    def test_forward_reset_navigation_and_password_never_erase_prior_word(self):
        self.engine.settings.update(typing_mode="forward")
        self.type_word("aa")
        self.engine.do_reset()
        before = len(self.engine.forwarded)
        self.assertFalse(self.key(IBus.KEY_BackSpace))
        self.assertEqual(len(self.engine.forwarded), before)
        self.type_word("tooi")
        self.assertFalse(self.key(IBus.KEY_Left))
        self.assertFalse(self.key(IBus.KEY_BackSpace))
        self.engine.do_set_content_type(IBus.InputPurpose.PASSWORD, 0)
        before = len(self.engine.forwarded)
        self.assertFalse(self.key("s"))
        self.assertEqual(len(self.engine.forwarded), before)

    def test_forwarded_events_cannot_reenter_composer(self):
        self.engine.settings.update(typing_mode="forward")
        self.type_word("aa")
        self.assertFalse(self.key(IBus.KEY_BackSpace, IBus.ModifierType.FORWARD_MASK))
        self.assertEqual(self.engine.composer.text, "â")

    def test_forward_waits_after_delete_and_preserves_queued_keys(self):
        self.engine.settings.update(typing_mode="forward")
        self.type_word("Pham")
        self.assertTrue(self.engine.do_process_key_event(ord('j'), 0, 0))
        self.assertEqual(self.engine.document, "Ph")
        self.assertIsNotNone(self.engine.forward_pending)
        self.assertTrue(self.engine.do_process_key_event(ord(' '), 0, 0))
        self.assertTrue(self.engine.do_process_key_event(ord('a'), 0, 0))
        self.assertEqual(self.engine.document, "Ph")
        self.engine.flush_forward()
        self.assertEqual(self.engine.document, "Phạm a")
        self.assertFalse(any(keyval == ord(' ') for keyval, _code, _state in self.engine.forwarded))
        self.assertEqual(self.engine.preedit, "")

    def test_forward_pending_insert_is_cancelled_when_focus_changes(self):
        self.engine.settings.update(typing_mode="forward")
        self.type_word("Pham")
        self.engine.do_process_key_event(ord('j'), 0, 0)
        self.engine.do_process_key_event(ord('x'), 0, 0)
        self.engine.do_focus_out()
        self.engine.document = "Other field"
        self.engine.cursor = self.engine.anchor = len(self.engine.document)
        self.engine.flush_forward()
        self.assertEqual(self.engine.document, "Other field")
        self.assertFalse(self.engine.forward_queue)

    def test_physical_backspace_passes_through_without_timer_or_fake_key(self):
        self.engine.settings.update(typing_mode="forward")
        self.type_word("Phamj")
        self.assertEqual(self.engine.document, "Phạm")
        before = list(self.engine.forwarded)
        for expected in ("Phạ", "Ph", "P", ""):
            self.assertFalse(self.key(IBus.KEY_BackSpace))
            self.assertEqual(self.engine.document, expected)
            self.assertEqual(self.engine.forward_text, expected)
            self.assertIsNone(self.engine.forward_pending)
            self.assertFalse(self.engine.scheduled)
            self.assertEqual(self.engine.forwarded, before)

    def test_queued_space_waits_for_macro_replacement_before_next_word(self):
        self.engine.settings.update(typing_mode="forward", macros_enabled=True, macros={"aa": "thay thế"})
        self.key('a')
        self.engine.do_process_key_event(ord('a'), 0, 0)
        self.engine.do_process_key_event(ord(' '), 0, 0)
        self.engine.do_process_key_event(ord('b'), 0, 0)
        self.engine.flush_forward()
        self.assertEqual(self.engine.document, "thay thế b")
        self.assertFalse(any(keyval == ord(' ') for keyval, _code, _state in self.engine.forwarded))


if __name__ == "__main__":
    unittest.main(verbosity=2)
