#!/usr/bin/python3
"""Bộ Gõ Việt: a per-user IBus engine, without keyboard hooks or network IO."""
import argparse
import signal
import sys
from pathlib import Path
import subprocess
from collections import deque
import gi

gi.require_version("IBus", "1.0")
from gi.repository import GLib, IBus
from composer import accepts_key, create_composer, expanded_text, feed_key, is_word_boundary
from settings import SettingsStore, VERSION
from direct import DirectBuffer, replacement_delta
from runtime_status import RuntimeStatus

ENGINE_ID = "bo-go-viet-telex"
COMPONENT = "org.freedesktop.IBus.BoGoViet"


class VietEngine(IBus.Engine):
    __gtype_name__ = "BoGoVietEngine"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.settings = SettingsStore()
        self.composer = create_composer(self.settings.value)
        self.vietnamese = self.settings.value["enabled"]
        self.private = False
        self.capabilities = 0
        self.direct = DirectBuffer()
        self.presentation = None
        self.runtime_status = RuntimeStatus()
        self.forward_text = ""
        self.forward_pending = None
        self.forward_generation = 0
        self.forward_queue = deque()

    def _sync_settings(self):
        if self.settings.refresh():
            self._commit()
            self.composer = create_composer(self.settings.value)
            self.vietnamese = self.settings.value["enabled"]
            self._properties()

    def _surrounding(self):
        if self.private or not self.capabilities & IBus.Capabilite.SURROUNDING_TEXT:
            return None
        try:
            text, cursor, anchor = self.get_surrounding_text()
            return (text.get_text(), cursor, anchor) if text is not None else None
        except GLib.Error:
            return None

    def _prepare_direct(self):
        if self.presentation == "direct" and not self.direct.matches(self._surrounding()):
            # The client moved the caret, selected text, edited, or has not yet
            # acknowledged our last commit. Leave its text untouched and stop
            # editing this word. Never guess how many backspaces to inject.
            self._clear()
            self.presentation = "preedit"
            self._report("preedit", "surrounding-not-confirmed")

    def _report(self, mode, reason=""):
        self.runtime_status.report(mode, reason, self.capabilities)

    def _write_direct(self, value):
        edit = self.direct.replace(value, self._surrounding())
        if edit is None:
            return False
        remove, insert = edit
        if remove:
            self.delete_surrounding_text(-remove, remove)
        if insert:
            self.commit_text(IBus.Text.new_from_string(insert))
        return True

    def _write_forward(self, value):
        # Explicit compatibility mode for clients that cannot provide surrounding
        # text. Only retain the current word, and clear it on reset/navigation/
        # shortcuts/focus changes. This mode cannot independently verify the caret.
        remove, insert = replacement_delta(self.forward_text, value)
        for _ in range(remove):
            self.forward_key_event(IBus.KEY_BackSpace, 14, 0)
            self.forward_key_event(IBus.KEY_BackSpace, 14, IBus.ModifierType.RELEASE_MASK)
        self.forward_text = value
        if not remove:
            if insert:
                self.commit_text(IBus.Text.new_from_string(insert))
            return
        if not insert:
            return
        # A client may enqueue forwarded keys but process CommitText immediately.
        # Return from ProcessKeyEvent and yield to its event loop before replacing
        # the removed suffix. Serialize subsequent physical keys behind this edit.
        generation = self.forward_generation
        self.forward_pending = self._schedule_forward(35 + 15 * remove,
            lambda: self._finish_forward(generation, insert))

    def _schedule_forward(self, delay, callback):
        return GLib.timeout_add(delay, callback)

    def _remove_forward_source(self, source):
        GLib.source_remove(source)

    def _finish_forward(self, generation, insert):
        if generation != self.forward_generation:
            return False
        self.forward_pending = None
        if insert and not self.private:
            self.commit_text(IBus.Text.new_from_string(insert))
        while self.forward_queue and self.forward_pending is None:
            keyval, keycode, state = self.forward_queue.popleft()
            if not self._process_key_event(keyval, keycode, state):
                if self.forward_pending is not None:
                    # Expanding a macro at this boundary scheduled another edit.
                    # Deliver the boundary only after the replacement is ready.
                    self.forward_queue.appendleft((keyval, keycode, state))
                    continue
                char = IBus.keyval_to_unicode(keyval)
                shortcut = state & (IBus.ModifierType.CONTROL_MASK | IBus.ModifierType.MOD1_MASK |
                                    IBus.ModifierType.SUPER_MASK | IBus.ModifierType.META_MASK | IBus.ModifierType.HYPER_MASK)
                if char and char.isprintable() and not shortcut:
                    # Mixing a queued synthetic Space with immediate CommitText
                    # lets some editors insert the next word before the space.
                    self.commit_text(IBus.Text.new_from_string(char))
                else:
                    self.forward_key_event(keyval, keycode, state)
                    generation = self.forward_generation
                    self.forward_pending = self._schedule_forward(35,
                        lambda: self._finish_forward(generation, ""))
        return False

    def _cancel_forward(self):
        self.forward_generation += 1
        if self.forward_pending is not None:
            self._report("forward", "pending-edit-cancelled-on-focus-or-reset")
            self._remove_forward_source(self.forward_pending)
            self.forward_pending = None
        self.forward_queue.clear()

    def _show_preedit(self, value):
        text = IBus.Text.new_from_string(value)
        if value:
            underline = IBus.AttrUnderline.SINGLE if self.settings.value["underline"] else IBus.AttrUnderline.NONE
            text.append_attribute(IBus.AttrType.UNDERLINE, underline, 0, len(value))
        self.update_preedit_text(text, len(value), bool(value))

    def _update(self):
        value = self.composer.text
        if self.presentation is None and value:
            if self.settings.value["typing_mode"] == "forward":
                self.presentation = "forward"
            else:
                use_direct = self.settings.value["typing_mode"] == "direct" and self.direct.begin(self._surrounding())
                self.presentation = "direct" if use_direct else "preedit"
            reason = ""
            if self.settings.value["typing_mode"] == "direct" and self.presentation != "direct":
                reason = "no-surrounding-support" if not self.capabilities & IBus.Capabilite.SURROUNDING_TEXT else "surrounding-unavailable-or-selection"
            self._report(self.presentation, reason)
        if self.presentation == "direct":
            self._write_direct(value)
        elif self.presentation == "forward":
            self._write_forward(value)
        else:
            self._show_preedit(value)

    def _clear(self):
        self.composer.clear()
        self.presentation = None
        self.direct.reset()
        self.forward_text = ""
        self._show_preedit("")

    def _commit(self, raw=False, expand=False):
        if raw:
            value = self.composer.raw
        elif expand:
            value = expanded_text(self.composer, self.settings.value)
        else:
            value = self.composer.text
        was_direct = self.presentation in ("direct", "forward")
        if was_direct and (raw or expand):
            if self.presentation == "forward":
                self._write_forward(value)
            else:
                self._write_direct(value)
        self._clear()
        if value and not was_direct:
            self.commit_text(IBus.Text.new_from_string(value))

    def _properties(self):
        props = IBus.PropList()
        prop = IBus.Property.new(
            "vietnamese", IBus.PropType.TOGGLE,
            IBus.Text.new_from_string("Tiếng Việt: Bật" if self.vietnamese else "Tiếng Việt: Tắt"),
            "", IBus.Text.new_from_string("Ctrl+Shift+Space: chuyển Việt / Anh"),
            True, True,
            IBus.PropState.CHECKED if self.vietnamese else IBus.PropState.UNCHECKED,
            None,
        )
        props.append(prop)
        for name, label in (("telex", "Telex"), ("vni", "VNI"), ("settings", "Thiết lập Bộ Gõ Việt…")):
            props.append(IBus.Property.new(name, IBus.PropType.NORMAL, IBus.Text.new_from_string(label),
                         "", IBus.Text.new_from_string(label), True, True, IBus.PropState.UNCHECKED, None))
        self.register_properties(props)

    def _toggle(self):
        self._commit()
        self.vietnamese = not self.vietnamese
        try:
            self.settings.update(enabled=self.vietnamese)
        except (OSError, ValueError) as exc:
            print(f"Không lưu được trạng thái: {exc}", file=sys.stderr)
        self._properties()

    def do_property_activate(self, name, state):
        if name == "vietnamese":
            self._toggle()
        elif name in ("telex", "vni"):
            self._commit()
            try:
                self.settings.update(input_method=name)
                self.composer = create_composer(self.settings.value)
            except (OSError, ValueError) as exc:
                print(f"Không lưu được kiểu gõ: {exc}", file=sys.stderr)
            self._properties()
        elif name == "settings":
            subprocess.Popen(["/usr/bin/python3", str(Path(__file__).with_name("preferences.py"))])

    def do_focus_in(self):
        self._sync_settings()
        if self.settings.value["typing_mode"] == "direct":
            self._surrounding()
        self._report("ready", "" if self.capabilities & IBus.Capabilite.SURROUNDING_TEXT else "no-surrounding-support")
        self._properties()

    def do_set_capabilities(self, caps):
        self.capabilities = caps
        self._report("ready", "" if caps & IBus.Capabilite.SURROUNDING_TEXT else "no-surrounding-support")

    def do_enable(self):
        if self.settings.value["typing_mode"] == "direct":
            self._surrounding()

    def do_focus_out(self):
        self._cancel_forward()
        self._commit()

    def do_reset(self):
        self._cancel_forward()
        self._clear()

    def do_disable(self):
        self._cancel_forward()
        self._commit()

    def do_set_content_type(self, purpose, hints):
        self.private = purpose in (IBus.InputPurpose.PASSWORD, IBus.InputPurpose.PIN) or bool(hints & IBus.InputHints.PRIVATE)
        if self.private:
            self._cancel_forward()
            self._clear()

    def do_process_key_event(self, keyval, keycode, state):
        if state & (IBus.ModifierType.RELEASE_MASK | IBus.ModifierType.FORWARD_MASK):
            return False
        if self.private:
            return False
        if self.forward_pending is not None:
            self.forward_queue.append((keyval, keycode, state))
            return True
        return self._process_key_event(keyval, keycode, state)

    def _process_key_event(self, keyval, keycode, state):
        self._prepare_direct()
        self._sync_settings()
        ctrl = bool(state & IBus.ModifierType.CONTROL_MASK)
        shift = bool(state & IBus.ModifierType.SHIFT_MASK)
        other = state & (IBus.ModifierType.MOD1_MASK | IBus.ModifierType.SUPER_MASK | IBus.ModifierType.META_MASK | IBus.ModifierType.HYPER_MASK)
        if keyval == IBus.KEY_space and ctrl and shift and not other:
            self._toggle()
            return True
        if not self.vietnamese:
            return False
        if keyval in (IBus.KEY_Shift_L, IBus.KEY_Shift_R, IBus.KEY_Control_L, IBus.KEY_Control_R,
                      IBus.KEY_Alt_L, IBus.KEY_Alt_R, IBus.KEY_Super_L, IBus.KEY_Super_R,
                      IBus.KEY_Caps_Lock, IBus.KEY_ISO_Level3_Shift):
            return False
        if ctrl or other:
            self._commit()
            return False
        if keyval == IBus.KEY_BackSpace:
            if not self.composer.text:
                return False
            previous = self.composer.text
            self.composer.backspace()
            if self.presentation == "forward" and self.composer.text == previous[:-1]:
                # Let the original physical Backspace reach the client. There is
                # no replacement to serialize, and no synthetic key or timer.
                self.forward_text = self.composer.text
                return False
            self._update()
            return True
        if keyval == IBus.KEY_Escape and self.composer.text:
            self._commit(raw=True)
            return True
        char = IBus.keyval_to_unicode(keyval)
        if accepts_key(char, self.settings.value):
            if len(self.composer.raw) >= 128:
                self._commit()
            feed_key(self.composer, char, self.settings.value)
            self._update()
            return True
        self._commit(expand=keyval in (IBus.KEY_space, IBus.KEY_Return, IBus.KEY_Tab) or is_word_boundary(char))
        return False


def component():
    value = IBus.Component.new(COMPONENT, "Bộ Gõ Việt", VERSION, "MIT", "Bộ Gõ Việt", "", "", "")
    value.add_engine(IBus.EngineDesc.new(ENGINE_ID, "Bộ Gõ Việt", "Telex / VNI • Unicode", "vi", "MIT", "Bộ Gõ Việt", "input-keyboard", "us"))
    return value


def main():
    parser = argparse.ArgumentParser(description="Bộ Gõ Việt – Telex / VNI")
    parser.add_argument("--ibus", action="store_true", help="Được IBus khởi chạy từ registry")
    args = parser.parse_args()
    IBus.init()
    loop = GLib.MainLoop()
    bus = IBus.Bus.new_async()
    factories = []

    def connected(_bus):
        try:
            # One owner per desktop session; start-up and manual runs may overlap.
            if bus.request_name(COMPONENT, IBus.BusNameFlag.DO_NOT_QUEUE) not in (1, 4):
                loop.quit()
                return
            factory = IBus.Factory.new(bus.get_connection())
            factory.add_engine(ENGINE_ID, VietEngine)
            factories[:] = [factory]
            if not args.ibus and not bus.register_component(component()):
                print("Không đăng ký được bộ gõ với IBus.", file=sys.stderr)
                loop.quit()
        except GLib.Error as exc:
            print(f"Không kết nối được với IBus: {exc.message}", file=sys.stderr)
            loop.quit()

    bus.connect("connected", connected)
    bus.connect("disconnected", lambda _bus: factories.clear())
    if bus.is_connected():
        connected(bus)
    for signum in (signal.SIGTERM, signal.SIGINT):
        GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signum, lambda: (loop.quit(), False)[1])
    loop.run()


if __name__ == "__main__":
    main()
