#!/usr/bin/python3
"""Add/remove this engine while preserving the user's other input sources."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time
import gi

gi.require_version("IBus", "1.0")
from gi.repository import Gio, GLib, IBus

ENGINE_ID = "bo-go-viet-telex"


def main():
    parser = argparse.ArgumentParser(description="Bật/gỡ nguồn bàn phím Bộ Gõ Việt trong GNOME")
    parser.add_argument("--remove", action="store_true", help="Chỉ gỡ nguồn khỏi tài khoản hiện tại")
    args = parser.parse_args()
    if os.geteuid() == 0:
        sys.exit("Chạy lệnh này trong tài khoản thường, KHÔNG dùng sudo.")
    settings = Gio.Settings.new("org.gnome.desktop.input-sources")
    if not settings.is_writable("sources"):
        sys.exit("Không sửa được nguồn bàn phím. Chạy trong Terminal của phiên Ubuntu đang đăng nhập.")
    sources = [tuple(item) for item in settings.get_value("sources").unpack()]
    source = ("ibus", ENGINE_ID)
    if args.remove:
        sources = [item for item in sources if item != source] or [("xkb", "us")]
    else:
        if not Path("/usr/share/ibus/component/bo-go-viet.xml").is_file():
            sys.exit("Chưa cài tệp bộ gõ. Chạy trước: sudo /usr/bin/python3 install.py")
        IBus.init()
        bus = IBus.Bus()
        if not bus.is_connected():
            sys.exit("Không kết nối được IBus. Đăng xuất/đăng nhập Ubuntu, rồi chạy lại lệnh này.")
        if not bus.get_engines_by_names([ENGINE_ID]):
            print("Đang làm mới IBus để nhận bộ gõ mới…")
            try:
                subprocess.run(["ibus", "restart"], check=True, timeout=15)
            except (subprocess.SubprocessError, OSError):
                sys.exit("Chưa làm mới được IBus. Đăng xuất/đăng nhập rồi chạy lại: python3 enable.py")
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                while GLib.MainContext.default().pending():
                    GLib.MainContext.default().iteration(False)
                if bus.is_connected() and bus.get_engines_by_names([ENGINE_ID]):
                    break
                time.sleep(0.1)
        if not bus.is_connected() or not bus.get_engines_by_names([ENGINE_ID]):
            sys.exit("IBus chưa nhận metadata. Đăng xuất/đăng nhập rồi chạy lại: python3 enable.py")
        if source not in sources:
            sources.append(source)
    if not settings.set_value("sources", GLib.Variant("a(ss)", sources)):
        sys.exit("Không cập nhật được nguồn bàn phím.")
    Gio.Settings.sync()
    print("Đã gỡ nguồn Bộ Gõ Việt." if args.remove else "Đã thêm Bộ Gõ Việt. Nhấn Super (Windows) + Space để chọn; Ctrl+Shift+Space chuyển Việt / Anh.")


if __name__ == "__main__":
    main()
