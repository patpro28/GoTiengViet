"""GTK smoke check with isolated preferences; requires a working display.

Usage: /usr/bin/python3 ui_check.py [snapshot-directory]
"""
import os
import argparse
from pathlib import Path
import sys
import tempfile
import time


def main():
    parser = argparse.ArgumentParser(description="Check native GTK UI with isolated preferences")
    parser.add_argument("snapshot_directory", nargs="?")
    parser.add_argument("--theme", choices=("system", "light", "dark"), default="system")
    parser.add_argument("--gtk-theme", help="GTK theme name for this test process only")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="bgv-ui-") as directory:
        os.environ["XDG_CONFIG_HOME"] = directory
        from preferences import Gtk, Gio, GLib, IBus, Preferences
        IBus.init()
        app = Gtk.Application(application_id="org.bogoviet.UICheck", flags=Gio.ApplicationFlags.NON_UNIQUE)
        app.register(None)
        gtk_settings = Gtk.Settings.get_default()
        if args.gtk_theme:
            gtk_settings.set_property("gtk-theme-name", args.gtk_theme)
        window = Preferences(app)
        if args.theme != "system":
            gtk_settings.set_property("gtk-application-prefer-dark-theme", args.theme == "dark")

        def settle():
            deadline = time.monotonic() + 0.3
            while time.monotonic() < deadline:
                while GLib.MainContext.default().pending():
                    GLib.MainContext.default().iteration(False)
                time.sleep(0.01)

        def snapshot(name):
            settle()
            if args.snapshot_directory:
                output = Path(args.snapshot_directory)
                output.mkdir(parents=True, exist_ok=True)
                width, height = window.get_allocated_width(), window.get_allocated_height()
                # Render our own widget directly. Wayland screen capture returns
                # black pixels, and python3-gi-cairo is optional on Ubuntu.
                import ctypes as c
                cairo = c.CDLL("libcairo.so.2")
                gtk = c.CDLL("libgtk-3.so.0")
                capsule = c.pythonapi.PyCapsule_GetPointer
                capsule.argtypes, capsule.restype = [c.py_object, c.c_char_p], c.c_void_p
                cairo.cairo_image_surface_create.argtypes = [c.c_int, c.c_int, c.c_int]
                cairo.cairo_image_surface_create.restype = c.c_void_p
                cairo.cairo_create.argtypes, cairo.cairo_create.restype = [c.c_void_p], c.c_void_p
                gtk.gtk_widget_draw.argtypes = [c.c_void_p, c.c_void_p]
                cairo.cairo_surface_write_to_png.argtypes = [c.c_void_p, c.c_char_p]
                cairo.cairo_destroy.argtypes = [c.c_void_p]
                cairo.cairo_surface_destroy.argtypes = [c.c_void_p]
                surface = cairo.cairo_image_surface_create(0, width, height)
                context = cairo.cairo_create(surface)
                try:
                    gtk.gtk_widget_draw(capsule(window.__gpointer__, None), context)
                    assert cairo.cairo_surface_write_to_png(surface, os.fsencode(output / f"{name}.png")) == 0
                finally:
                    cairo.cairo_destroy(context)
                    cairo.cairo_surface_destroy(surface)

        def check_theme_contrast():
            settle()
            state = Gtk.StateFlags.NORMAL
            def rgb(color, background):
                return tuple(color.alpha * value + (1 - color.alpha) * base for value, base in zip((color.red, color.green, color.blue), background))
            def luminance(color):
                linear = [value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4 for value in color]
                return sum(a * b for a, b in zip(linear, (.2126, .7152, .0722)))
            def assert_contrast(widget, background):
                foreground = rgb(widget.get_style_context().get_color(state), background)
                a, b = sorted((luminance(foreground), luminance(background)))
                assert (b + .05) / (a + .05) >= 4.5, f"Unreadable {type(widget).__name__}: {foreground} on {background}"
            color = window.get_style_context().get_background_color(state)
            window_background = (color.red, color.green, color.blue)
            if args.theme == "dark":
                assert luminance(window_background) < .3, "Dark GTK variant not active"
            elif args.theme == "light":
                assert luminance(window_background) > .5, "Light GTK variant not active"
            for nav in window.pages.values():
                sidebar = nav.get_parent().get_style_context().get_background_color(state)
                background = rgb(sidebar, window_background)
                if nav.get_active():
                    background = rgb(nav.get_style_context().get_background_color(nav.get_state_flags()), background)
                assert_contrast(nav.get_child().get_children()[1], background)
            close_background = rgb(window.close_button.get_style_context().get_background_color(state), window_background)
            assert_contrast(window.close_button.get_child(), close_background)
            title_buttons = []
            def visit(widget):
                if isinstance(widget, Gtk.Button) and widget.get_style_context().has_class("titlebutton"):
                    title_buttons.append(widget)
                if isinstance(widget, Gtk.Container):
                    widget.forall(visit)
            visit(window.get_titlebar())
            assert title_buttons, "Titlebar buttons missing"
            for control in title_buttons:
                assert_contrast(control, rgb(control.get_style_context().get_background_color(state), window_background))

        try:
            snapshot("general")
            check_theme_contrast()
            assert window.preview_label.get_text() == "Tôi yêu tiếng Việt"
            window.typing_mode.set_active_id("direct")
            assert window.store.value["typing_mode"] == "direct"
            window.typing_mode.set_active_id("forward")
            assert window.store.value["typing_mode"] == "forward"
            window.underline.set_active(True)
            assert window.store.value["underline"] is True
            window.underline.set_active(False)
            window.typing_mode.set_active_id("preedit")
            window.method.set_active_id("vni")
            window.raw_entry.set_text("To6i ye6u tie61ng Vie65t")
            assert window.preview_label.get_text() == "Tôi yêu tiếng Việt"
            window.navigate(None, "macros")
            window.macro_key.set_text("camon")
            window.macro_value.set_text("Cảm ơn bạn!")
            window.add_macro()
            assert window.store.value["macros"]["camon"] == "Cảm ơn bạn!"
            window.macro_switch.set_active(True)
            snapshot("macros")
            window.remove_macro(None, "camon")
            assert "camon" not in window.store.value["macros"]
            window.navigate(None, "convert")
            window.convert("strip")
            buffer = window.result_text.get_buffer()
            assert buffer.get_text(*buffer.get_bounds(), True) == "Tieng Viet that dep. Ban co nghi vay khong?"
            snapshot("convert")
            for name in ("backup", "about"):
                window.navigate(None, name)
                snapshot(name)
            if args.theme != "system":
                args.theme = "light" if args.theme == "dark" else "dark"
                gtk_settings.set_property("gtk-application-prefer-dark-theme", args.theme == "dark")
                check_theme_contrast()
                snapshot("theme-switched")
            window.close_button.clicked()
            settle()
            assert not window.get_visible()
            print("PASS: all five GTK pages, theme contrast and switching, live VNI preview, settings persistence, macro add/delete, conversion, Close button")
        finally:
            window.destroy()


if __name__ == "__main__":
    main()
