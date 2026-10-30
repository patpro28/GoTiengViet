#!/usr/bin/python3
"""Native GTK preferences for Bộ Gõ Việt. Never captures global key events."""
import json
from pathlib import Path
import sys
import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("IBus", "1.0")
from gi.repository import Gdk, Gio, GLib, Gtk, IBus
from composer import preview, convert_text
from settings import SettingsStore, VERSION, validate
from runtime_status import status_path

ROOT = Path(__file__).resolve().parent
CSS = b"""
@define-color bgv_accent mix(@theme_fg_color, #168263, 0.6);
.bo-go-viet { background: @theme_bg_color; color: @theme_fg_color; }
.bo-go-viet label, .bo-go-viet image { color: inherit; }
.bo-go-viet headerbar { background: @theme_bg_color; color: @theme_fg_color; border-bottom: 1px solid alpha(@theme_fg_color, 0.14); box-shadow: none; }
.bo-go-viet headerbar .subtitle { color: alpha(@theme_fg_color, 0.72); }
.bo-go-viet headerbar button.titlebutton { color: @theme_fg_color; background: alpha(@theme_fg_color, 0.06); border-color: transparent; }
.bo-go-viet headerbar button.titlebutton:hover { background: alpha(@theme_fg_color, 0.16); }
.bo-go-viet headerbar button.titlebutton.close:hover { background: #bd3434; color: #ffffff; }
.bo-go-viet .sidebar { background: mix(@theme_bg_color, @theme_fg_color, 0.035); border-right: 1px solid alpha(@theme_fg_color, 0.12); }
.bo-go-viet .brand { font-size: 19px; font-weight: 700; }
.bo-go-viet .muted { color: alpha(@theme_fg_color, 0.72); }
.bo-go-viet .eyebrow { color: @bgv_accent; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
.bo-go-viet .hero-title { font-size: 32px; font-weight: 800; letter-spacing: -1px; }
.bo-go-viet .page-title { font-size: 26px; font-weight: 700; }
.bo-go-viet .section-title { font-size: 15px; font-weight: 700; }
.bo-go-viet .card { background: @theme_base_color; color: @theme_fg_color; border: 1px solid alpha(@theme_fg_color, 0.14); border-radius: 12px; padding: 18px; }
.bo-go-viet .hero { background: mix(@theme_base_color, @bgv_accent, 0.1); border-color: alpha(@bgv_accent, 0.24); padding: 24px; }
.bo-go-viet .sample { color: @bgv_accent; font-size: 54px; font-weight: 700; }
.bo-go-viet .preview { font-size: 21px; color: @bgv_accent; }
.bo-go-viet .nav { color: @theme_fg_color; background: transparent; border: none; border-radius: 8px; box-shadow: none; padding: 12px; }
.bo-go-viet .nav:hover { background: alpha(@theme_fg_color, 0.07); }
.bo-go-viet .nav:checked { background: alpha(@bgv_accent, 0.17); color: @theme_fg_color; font-weight: 700; }
.bo-go-viet .nav:checked image { color: @bgv_accent; }
.bo-go-viet button { color: @theme_fg_color; background: mix(@theme_base_color, @theme_bg_color, 0.5); border-color: alpha(@theme_fg_color, 0.22); border-radius: 7px; padding: 7px 12px; }
.bo-go-viet button:hover { background: mix(@theme_base_color, @theme_fg_color, 0.1); }
.bo-go-viet button.suggested-action { background: #16745a; color: #ffffff; border-color: #16745a; }
.bo-go-viet button.suggested-action:hover { background: #1a8667; }
.bo-go-viet switch:checked { background: #16745a; border-color: #16745a; }
.bo-go-viet entry, .bo-go-viet textview, .bo-go-viet textview text { color: @theme_text_color; background: @theme_base_color; caret-color: @theme_text_color; }
.bo-go-viet entry { border: 1px solid alpha(@theme_fg_color, 0.22); border-radius: 7px; padding: 9px; }
.bo-go-viet entry selection, .bo-go-viet textview text selection { background: @theme_selected_bg_color; color: @theme_selected_fg_color; }
.bo-go-viet combobox button { color: @theme_text_color; background: @theme_base_color; }
.bo-go-viet combobox cellview, .bo-go-viet combobox arrow { color: inherit; background: transparent; }
.bo-go-viet textview { padding: 12px; }
.bo-go-viet .status { font-size: 12px; color: alpha(@theme_fg_color, 0.72); }
.bo-go-viet .key { color: @theme_fg_color; background: alpha(@theme_fg_color, 0.055); border: 1px solid alpha(@theme_fg_color, 0.14); border-radius: 5px; padding: 5px 8px; font-family: monospace; }
.bo-go-viet .macro-row { padding: 10px 0; border-bottom: 1px solid alpha(@theme_fg_color, 0.1); }
"""


def box(vertical=True, spacing=12):
    return Gtk.Box(orientation=Gtk.Orientation.VERTICAL if vertical else Gtk.Orientation.HORIZONTAL, spacing=spacing)


def label(text, style=None):
    widget = Gtk.Label(label=text, xalign=0)
    widget.set_line_wrap(True)
    widget.set_max_width_chars(65)
    if style:
        widget.get_style_context().add_class(style)
    return widget


def button(text, callback, primary=False):
    widget = Gtk.Button(label=text)
    if primary:
        widget.get_style_context().add_class("suggested-action")
    widget.connect("clicked", callback)
    return widget


def card(style=None):
    widget = box()
    widget.get_style_context().add_class("card")
    if style:
        widget.get_style_context().add_class(style)
    return widget


class Preferences(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Bộ Gõ Việt")
        self.set_default_size(1000, 780)
        self.set_size_request(820, 640)
        self.store = SettingsStore()
        self.loading = False
        self.get_style_context().add_class("bo-go-viet")
        self.follow_system_appearance()
        self.set_icon_from_file(str(ROOT / "assets/bo-go-viet.svg"))
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_screen(self.get_screen(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        header = Gtk.HeaderBar(title="Bộ Gõ Việt", subtitle="Không gian nhỏ cho những ý tưởng lớn")
        header.set_show_close_button(True)
        header.set_decoration_layout("menu:minimize,maximize,close")
        self.set_titlebar(header)
        layout = box(False, 0)
        self.add(layout)
        sidebar = box(spacing=6)
        sidebar.set_size_request(210, -1)
        sidebar.set_border_width(18)
        sidebar.get_style_context().add_class("sidebar")
        layout.pack_start(sidebar, False, False, 0)
        brand = box(False, 10)
        logo = Gtk.Image.new_from_file(str(ROOT / "assets/bo-go-viet.svg"))
        logo.set_pixel_size(36)
        # SVG loaded at the requested size rather than its intrinsic 128px.
        from gi.repository import GdkPixbuf
        logo.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_scale(str(ROOT / "assets/bo-go-viet.svg"), 36, 36, True))
        brand.pack_start(logo, False, False, 0)
        brand.pack_start(label("Bộ Gõ Việt", "brand"), False, False, 0)
        sidebar.pack_start(brand, False, False, 14)
        sidebar.pack_start(label("CỦA BẠN, THEO CÁCH BẠN GÕ", "eyebrow"), False, False, 12)
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE, transition_duration=140)
        content = box(spacing=0)
        layout.pack_start(content, True, True, 0)
        content.pack_start(self.stack, True, True, 0)
        actions = box(False, 16)
        actions.set_margin_start(30)
        actions.set_margin_end(30)
        actions.set_margin_top(12)
        actions.set_margin_bottom(16)
        self.notice = label("Cài đặt được lưu tự động trên máy này.", "status")
        actions.pack_start(self.notice, True, True, 0)
        self.close_button = button("Đóng", lambda _: self.close())
        self.close_button.set_size_request(100, -1)
        self.close_button.set_valign(Gtk.Align.CENTER)
        self.close_button.set_tooltip_text("Đóng cửa sổ thiết lập")
        actions.pack_end(self.close_button, False, False, 0)
        content.pack_start(actions, False, False, 0)
        self.pages = {}
        for key, title, icon, builder in (
            ("general", "Tổng quan", "preferences-desktop-keyboard-symbolic", self.general),
            ("macros", "Gõ tắt", "view-list-symbolic", self.macros),
            ("convert", "Chuyển văn bản", "edit-select-all-symbolic", self.conversion),
            ("backup", "Sao lưu & khôi phục", "document-save-symbolic", self.backup),
            ("about", "Hướng dẫn & giới thiệu", "help-about-symbolic", self.about),
        ):
            nav = Gtk.ToggleButton()
            nav.get_style_context().add_class("nav")
            row = box(False, 10)
            row.pack_start(Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU), False, False, 0)
            row.pack_start(label(title), False, False, 0)
            nav.add(row)
            nav.connect("clicked", self.navigate, key)
            sidebar.pack_start(nav, False, False, 0)
            self.pages[key] = nav
            page = box(spacing=18)
            page.set_border_width(30)
            builder(page)
            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
            scroll.add(page)
            self.stack.add_named(scroll, key)
        footer = box(spacing=6)
        footer.pack_start(label("LOCAL FIRST", "eyebrow"), False, False, 0)
        footer.pack_start(label("Riêng tư. Nhẹ nhàng. Tiếng Việt.", "muted"), False, False, 0)
        footer.pack_start(label(f"Phiên bản {VERSION} · Ubuntu / IBus", "muted"), False, False, 0)
        sidebar.pack_end(footer, False, False, 12)
        self.navigate(None, "general")
        self.show_all()
        self.refresh_controls()
        if self.store.error:
            self.message("Không đọc được cấu hình: " + self.store.error)
        self.bus = IBus.Bus.new_async()
        self.bus.connect("connected", lambda *_: self.check_bus())
        self.bus.connect("disconnected", lambda *_: self.check_bus())
        self.check_bus()
        self.connect("focus-in-event", self.focused)

    def follow_system_appearance(self):
        # GTK3 does not always pick up GNOME's light/dark preference on its own.
        # Change only this process's GtkSettings, never the desktop preference.
        source = Gio.SettingsSchemaSource.get_default()
        schema = source.lookup("org.gnome.desktop.interface", True) if source else None
        if schema is None or not schema.has_key("color-scheme"):
            return
        desktop = Gio.Settings.new_full(schema, None, None)
        def update_appearance(*_):
            Gtk.Settings.get_default().set_property("gtk-application-prefer-dark-theme", desktop.get_string("color-scheme") == "prefer-dark")
        update_appearance()
        handler = desktop.connect("changed::color-scheme", update_appearance)
        self.connect("destroy", lambda *_: desktop.disconnect(handler))

    def navigate(self, _button, name):
        if getattr(self, "navigating", False):
            return
        self.navigating = True
        self.stack.set_visible_child_name(name)
        for key, nav in self.pages.items():
            nav.set_active(key == name)
        self.navigating = False

    def message(self, text):
        self.notice.set_text(text)

    def save(self, **changes):
        if self.loading:
            return
        try:
            self.store.update(**changes)
            self.message("Đã lưu · Áp dụng cho bộ gõ ở phím tiếp theo.")
        except (OSError, ValueError) as exc:
            self.message("Không lưu được: " + str(exc))
        self.refresh_controls()

    def focused(self, *_):
        if self.store.refresh():
            self.refresh_controls()
        self.check_bus()
        return False

    def refresh_controls(self):
        self.loading = True
        value = self.store.value
        self.enabled.set_active(value["enabled"])
        self.method.set_active_id(value["input_method"])
        self.typing_mode.set_active_id(value["typing_mode"])
        self.underline.set_active(value["underline"])
        self.modern.set_active(value["modern_tone"])
        self.macro_switch.set_active(value["macros_enabled"])
        self.loading = False
        samples = {"telex": "Tooi yeeu tieengs Vieetj", "vni": "To6i ye6u tie61ng Vie65t"}
        if self.raw_entry.get_text() in samples.values():
            self.raw_entry.set_text(samples[value["input_method"]])
        self.update_preview()
        self.render_macros()

    def title(self, page, title, subtitle):
        group = box(spacing=6)
        group.pack_start(label(title, "page-title"), False, False, 0)
        group.pack_start(label(subtitle, "muted"), False, False, 0)
        page.pack_start(group, False, False, 0)

    def option(self, parent, title, subtitle, control):
        row = box(False, 18)
        text = box(spacing=4)
        text.pack_start(label(title, "section-title"), False, False, 0)
        text.pack_start(label(subtitle, "muted"), False, False, 0)
        row.pack_start(text, True, True, 0)
        control.set_valign(Gtk.Align.CENTER)
        row.pack_end(control, False, False, 0)
        parent.pack_start(row, False, False, 0)

    def general(self, page):
        hero = card("hero")
        hero.pack_start(label("BỘ GÕ TIẾNG VIỆT CHO UBUNTU", "eyebrow"), False, False, 0)
        row = box(False, 30)
        row.pack_start(label("Gõ tự nhiên.\nViết trọn ý.", "hero-title"), True, True, 0)
        row.pack_end(label("ấ", "sample"), False, False, 16)
        hero.pack_start(row, False, False, 0)
        hero.pack_start(label("Một bộ gõ gọn gàng, theo đúng cách bạn viết mỗi ngày.", "muted"), False, False, 0)
        page.pack_start(hero, False, False, 0)
        self.connection = label("Đang kiểm tra kết nối IBus…", "status")
        page.pack_start(self.connection, False, False, 0)
        self.input_status = label("", "status")
        page.pack_start(self.input_status, False, False, 0)
        options = card()
        self.enabled = Gtk.Switch()
        self.enabled.connect("notify::active", lambda widget, _: self.save(enabled=widget.get_active()))
        self.option(options, "Gõ tiếng Việt", "Chuyển Việt / Anh với Ctrl + Shift + Space", self.enabled)
        options.pack_start(Gtk.Separator(), False, False, 2)
        self.method = Gtk.ComboBoxText()
        self.method.append("telex", "Telex · aa, aw, s, f…")
        self.method.append("vni", "VNI · 1, 2, 3, 6, 7…")
        self.method.connect("changed", lambda widget: self.save(input_method=widget.get_active_id()))
        self.option(options, "Kiểu gõ", "Unicode chuẩn · dùng với phông chữ hiện đại", self.method)
        options.pack_start(Gtk.Separator(), False, False, 2)
        self.typing_mode = Gtk.ComboBoxText()
        self.typing_mode.append("preedit", "Soạn từ · tương thích")
        self.typing_mode.append("direct", "Nhập trực tiếp · thử nghiệm")
        self.typing_mode.append("forward", "Trực tiếp qua phím · tương thích")
        self.typing_mode.connect("changed", lambda widget: self.save(typing_mode=widget.get_active_id()))
        self.option(options, "Cách nhập", "Trực tiếp: ứng dụng nhận chữ sau từng phím.", self.typing_mode)
        options.pack_start(label("Nhập trực tiếp cần ứng dụng hỗ trợ sửa văn bản quanh con trỏ. Nếu vẫn có gạch chân, thử Trực tiếp qua phím. Chế độ qua phím gửi Backspace để thay dấu; hãy chốt từ bằng Space trước khi bấm chuột đổi vị trí.", "muted"), False, False, 0)
        options.pack_start(Gtk.Separator(), False, False, 2)
        self.underline = Gtk.Switch()
        self.underline.connect("notify::active", lambda widget, _: self.save(underline=widget.get_active()))
        self.option(options, "Gạch chân khi soạn", "Tắt để gửi phần chữ đang soạn không có gạch chân.\nMột số ứng dụng có thể tự áp dụng cách hiển thị riêng.", self.underline)
        options.pack_start(Gtk.Separator(), False, False, 2)
        self.modern = Gtk.Switch()
        self.modern.connect("notify::active", lambda widget, _: self.save(modern_tone=widget.get_active()))
        self.option(options, "Đặt dấu kiểu mới", "Bật: hoà, khoẻ, thuỷ · Tắt: hòa, khỏe, thủy", self.modern)
        page.pack_start(options, False, False, 0)
        test = card()
        test.pack_start(label("Thử một chút tiếng Việt", "section-title"), False, False, 0)
        test.pack_start(label("Nhập chuỗi phím gốc để xem quy tắc của kiểu gõ đã chọn.", "muted"), False, False, 0)
        self.raw_entry = Gtk.Entry(max_length=512)
        self.raw_entry.set_property("im-module", "gtk-im-context-simple")
        self.raw_entry.set_input_purpose(Gtk.InputPurpose.TERMINAL)
        self.raw_entry.set_text("Tooi yeeu tieengs Vieetj")
        self.raw_entry.connect("changed", lambda *_: self.update_preview())
        test.pack_start(self.raw_entry, False, False, 0)
        self.preview_label = label("", "preview")
        self.preview_label.set_selectable(True)
        test.pack_start(self.preview_label, False, False, 0)
        self.hint = label("", "muted")
        test.pack_start(self.hint, False, False, 0)
        page.pack_start(test, False, False, 0)

    def update_preview(self):
        if not hasattr(self, "preview_label"):
            return
        value = self.store.value
        raw = self.raw_entry.get_text()
        self.preview_label.set_text(preview(raw, value) if value["enabled"] else raw)
        self.hint.set_text("Telex: tieengs → tiếng · dd → đ · Esc: trả phím gốc" if value["input_method"] == "telex" else "VNI: tie61ng → tiếng · d9 → đ · 0: bỏ dấu thanh")
        self.raw_entry.set_placeholder_text("Tooi yeeu tieengs Vieetj" if value["input_method"] == "telex" else "To6i ye6u tie61ng Vie65t")

    def check_bus(self):
        if not hasattr(self, "bus"):
            return
        if not self.bus.is_connected():
            text = "○ Chưa kết nối IBus · Bạn vẫn có thể thử gõ và cài đặt."
        else:
            try:
                active = self.bus.get_global_engine()
                if active and active.get_name() == "bo-go-viet-telex":
                    text = "● Bộ Gõ Việt đang được chọn trong IBus"
                else:
                    text = "○ IBus đã kết nối · Nhấn Super + Space để chọn Bộ Gõ Việt."
            except GLib.Error:
                text = "○ IBus đã kết nối · Xem Hướng dẫn để bật bộ gõ."
        self.connection.set_text(text)
        detail = ""
        path = status_path()
        if self.store.value["typing_mode"] in ("direct", "forward") and path is not None:
            try:
                state = json.loads(path.read_text(encoding="utf-8"))
                last = state.get("last_typing")
                if last and Path(f"/proc/{int(state['pid'])}").exists():
                    if last["mode"] == "direct":
                        detail = "Lần gõ gần nhất: nhập trực tiếp."
                    elif last["mode"] == "forward":
                        detail = "Lần gõ gần nhất: trực tiếp qua phím, không dùng vùng soạn từ."
                    else:
                        reasons = {
                            "no-surrounding-support": "ứng dụng không hỗ trợ văn bản quanh con trỏ",
                            "surrounding-unavailable-or-selection": "chưa có văn bản quanh con trỏ hoặc đang chọn chữ",
                            "surrounding-not-confirmed": "ứng dụng chưa xác nhận nội dung vừa nhập hoặc con trỏ đã đổi",
                        }
                        detail = "Lần gõ gần nhất: soạn từ — " + reasons.get(last["reason"], "chế độ tương thích") + "."
            except (OSError, ValueError, KeyError, TypeError):
                pass
        self.input_status.set_text(detail)

    def macros(self, page):
        self.title(page, "Ít phím hơn. Nhiều ý hơn.", "Biến các từ viết tắt quen thuộc thành nội dung đầy đủ.")
        top = card()
        self.macro_switch = Gtk.Switch()
        self.macro_switch.connect("notify::active", lambda widget, _: self.save(macros_enabled=widget.get_active()))
        self.option(top, "Bật gõ tắt", "Thay thế khi nhấn Space, Enter, Tab hoặc dấu câu.", self.macro_switch)
        page.pack_start(top, False, False, 0)
        editor = card()
        editor.pack_start(label("Thêm hoặc sửa từ viết tắt", "section-title"), False, False, 0)
        self.macro_key = Gtk.Entry(placeholder_text="Viết tắt, ví dụ: camon", max_length=32)
        self.macro_value = Gtk.Entry(placeholder_text="Thay bằng: Cảm ơn bạn rất nhiều!")
        editor.pack_start(self.macro_key, False, False, 0)
        editor.pack_start(self.macro_value, False, False, 0)
        editor.pack_start(button("Lưu từ viết tắt", self.add_macro, True), False, False, 0)
        editor.pack_start(label("Phân biệt chữ hoa/thường. Chỉ áp dụng ở chế độ tiếng Việt.\nNhập lại cùng từ viết tắt để cập nhật nội dung.", "muted"), False, False, 0)
        page.pack_start(editor, False, False, 0)
        self.macro_list = card()
        page.pack_start(self.macro_list, False, False, 0)

    def add_macro(self, *_):
        self.store.refresh()
        macros = dict(self.store.value["macros"])
        macros[self.macro_key.get_text().strip()] = self.macro_value.get_text()
        try:
            validate(dict(self.store.value, macros=macros))
        except ValueError as exc:
            self.message(str(exc))
            return
        self.save(macros=macros)

    def remove_macro(self, _button, key):
        self.store.refresh()
        macros = dict(self.store.value["macros"])
        macros.pop(key, None)
        self.save(macros=macros)

    def render_macros(self):
        if not hasattr(self, "macro_list"):
            return
        for child in self.macro_list.get_children():
            child.destroy()
        macros = self.store.value["macros"]
        self.macro_list.pack_start(label(f"Từ điển của bạn · {len(macros)} mục", "section-title"), False, False, 0)
        for key, value in sorted(macros.items()):
            row = box(False, 12)
            row.get_style_context().add_class("macro-row")
            key_label = label(key, "key")
            key_label.set_size_request(64, -1)
            row.pack_start(key_label, False, False, 0)
            row.pack_start(label(value), True, True, 0)
            remove = button("Xóa", lambda widget, k=key: self.remove_macro(widget, k))
            row.pack_end(remove, False, False, 0)
            self.macro_list.pack_start(row, False, False, 0)
        if not macros:
            self.macro_list.pack_start(label("Chưa có từ viết tắt. Thêm mục đầu tiên ở phía trên.", "muted"), False, False, 0)
        self.macro_list.show_all()

    def conversion(self, page):
        self.title(page, "Chỉnh chữ, trong một chạm.", "Dán văn bản Unicode, chọn cách chuyển rồi sao chép kết quả.")
        group = card()
        self.source_text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR)
        self.source_text.get_buffer().set_text("Tiếng Việt thật đẹp. Bạn có nghĩ vậy không?")
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(160)
        scroll.add(self.source_text)
        group.pack_start(label("Văn bản gốc", "section-title"), False, False, 0)
        group.pack_start(scroll, False, False, 0)
        row = box(False, 6)
        for mode, title in (("strip", "Bỏ dấu"), ("upper", "CHỮ HOA"), ("lower", "chữ thường"), ("title", "Hoa Đầu Từ")):
            row.pack_start(button(title, lambda _, m=mode: self.convert(m)), True, True, 0)
        group.pack_start(row, False, False, 0)
        self.result_text = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, editable=False)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(160)
        scroll.add(self.result_text)
        group.pack_start(label("Kết quả", "section-title"), False, False, 0)
        group.pack_start(scroll, False, False, 0)
        group.pack_start(button("Sao chép kết quả", self.copy_result, True), False, False, 0)
        page.pack_start(group, False, False, 0)

    def convert(self, mode):
        buffer = self.source_text.get_buffer()
        self.result_text.get_buffer().set_text(convert_text(buffer.get_text(*buffer.get_bounds(), True), mode))

    def copy_result(self, *_):
        buffer = self.result_text.get_buffer()
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(buffer.get_text(*buffer.get_bounds(), True), -1)
        self.message("Đã sao chép kết quả.")

    def backup(self, page):
        self.title(page, "Thiết lập theo bạn đi mọi nơi.", "Lưu kiểu gõ, cách đặt dấu và toàn bộ từ viết tắt vào một tệp JSON.")
        group = card()
        group.pack_start(label("Một tệp. Đủ những gì bạn cần.", "section-title"), False, False, 0)
        group.pack_start(label("Bản sao lưu chỉ chứa thiết lập và từ viết tắt bạn thêm. Nội dung bạn gõ trong ứng dụng không được ghi lại.", "muted"), False, False, 0)
        group.pack_start(button("Xuất bản sao lưu…", lambda *_: self.choose_backup(False), True), False, False, 0)
        group.pack_start(button("Khôi phục từ tệp…", lambda *_: self.choose_backup(True)), False, False, 0)
        group.pack_start(label("Khôi phục sẽ thay thế cấu hình hiện tại. Hãy xuất bản sao lưu trước nếu muốn giữ lại.", "muted"), False, False, 0)
        page.pack_start(group, False, False, 0)

    def choose_backup(self, restoring):
        dialog = Gtk.FileChooserDialog(title="Khôi phục cấu hình" if restoring else "Xuất cấu hình", transient_for=self,
                                      action=Gtk.FileChooserAction.OPEN if restoring else Gtk.FileChooserAction.SAVE)
        dialog.add_buttons("Hủy", Gtk.ResponseType.CANCEL, "Mở" if restoring else "Lưu", Gtk.ResponseType.OK)
        if not restoring:
            dialog.set_current_name("bo-go-viet-backup.json")
            dialog.set_do_overwrite_confirmation(True)
        filter_ = Gtk.FileFilter()
        filter_.set_name("Cấu hình JSON")
        filter_.add_pattern("*.json")
        dialog.add_filter(filter_)
        if dialog.run() == Gtk.ResponseType.OK:
            path = Path(dialog.get_filename())
            try:
                if restoring:
                    if path.stat().st_size > 5_000_000:
                        raise ValueError("Tệp quá lớn.")
                    value = validate(json.loads(path.read_text(encoding="utf-8")))
                    self.store.save(value)
                    self.refresh_controls()
                else:
                    if not self.store.reload():
                        raise ValueError(self.store.error)
                    path.write_text(json.dumps(self.store.value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                self.message("Đã khôi phục cấu hình." if restoring else "Đã xuất bản sao lưu.")
            except (OSError, ValueError, UnicodeError) as exc:
                self.message("Không hoàn tất: " + str(exc))
        dialog.destroy()

    def about(self, page):
        self.title(page, "Chào bạn, mình là Bộ Gõ Việt.", f"Phiên bản {VERSION} · Phát triển cho Ubuntu GNOME với IBus")
        guide = card()
        guide.pack_start(label("Bắt đầu trong ba bước", "section-title"), False, False, 0)
        for text in ("1. Cài tệp bộ gõ từ Terminal trong thư mục mã nguồn:",
                     "sudo /usr/bin/python3 install.py",
                     "2. Thêm nguồn bàn phím bằng tài khoản thường:",
                     "/usr/bin/python3 enable.py",
                     "3. Nhấn Super + Space và chọn Bộ Gõ Việt."):
            line = label(text, "key" if text.startswith(("sudo", "/usr")) else None)
            line.set_selectable(True)
            guide.pack_start(line, False, False, 0)
        guide.pack_start(label("Nếu IBus chưa nhận bộ gõ, đăng xuất rồi đăng nhập lại. Cửa sổ này dùng để cài đặt; IBus xử lý việc gõ trong các ứng dụng.", "muted"), False, False, 0)
        page.pack_start(guide, False, False, 0)
        keys = card()
        keys.pack_start(label("Nhớ vài phím, viết thật thoải mái", "section-title"), False, False, 0)
        for title, detail in (("Ctrl + Shift + Space", "Chuyển tiếng Việt / tiếng Anh"), ("Esc", "Chốt chuỗi phím gốc của từ đang gõ"),
                              ("Backspace", "Xóa một ký tự đang hiển thị"), ("Space / Enter", "Chốt từ, áp dụng gõ tắt nếu đã bật")):
            row = box(False, 16)
            row.pack_start(label(title, "key"), False, False, 0)
            row.pack_end(label(detail, "muted"), True, True, 0)
            keys.pack_start(row, False, False, 0)
        page.pack_start(keys, False, False, 0)
        page.pack_start(label("Lấy cảm hứng từ XKey. Mã nguồn Python/GTK độc lập cho Linux, giấy phép MIT.\nChạy cục bộ, không gửi nội dung gõ qua mạng. Chưa có Smart Switch, kiểm tra chính tả, dịch thuật hoặc bảng mã TCVN3/VNI Windows.", "muted"), False, False, 0)


class Application(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.bogoviet.Preferences", flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        window = self.get_active_window()
        if window is None:
            window = Preferences(self)
        window.present()


if __name__ == "__main__":
    IBus.init()
    sys.exit(Application().run(sys.argv))
