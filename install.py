#!/usr/bin/python3
"""Install static IBus metadata so GNOME can discover the engine reliably."""
import argparse
import os
from pathlib import Path
import shutil
import sys
import xml.etree.ElementTree as ET
from settings import VERSION

DESTINATION = Path("/usr/local/share/bo-go-viet")
METADATA = Path("/usr/share/ibus/component/bo-go-viet.xml")
DESKTOP = Path("/usr/local/share/applications/bo-go-viet.desktop")
FILES = ("engine.py", "telex.py", "composer.py", "direct.py", "runtime_status.py", "settings.py", "preferences.py", "assets/bo-go-viet.svg", "demo.py", "enable.py", "install.py", "README.md", "LICENSE")


def desktop_entry():
    return ("[Desktop Entry]\nType=Application\nName=Bộ Gõ Việt\n"
            "Comment=Thiết lập bộ gõ tiếng Việt Telex / VNI\n"
            f'Exec=/usr/bin/python3 "{DESTINATION}/preferences.py"\n'
            f"Icon={DESTINATION}/assets/bo-go-viet.svg\n"
            "Terminal=false\nCategories=Settings;\nKeywords=Vietnamese;Telex;VNI;IBus;\n")


def component_xml():
    component = ET.Element("component")
    fields = {
        "name": "org.freedesktop.IBus.BoGoViet",
        "description": "Bộ Gõ Việt – Telex / VNI",
        "exec": f"/usr/bin/python3 {DESTINATION}/engine.py --ibus",
        "version": VERSION, "author": "Bộ Gõ Việt", "license": "MIT",
        "homepage": "", "textdomain": "",
    }
    for key, value in fields.items():
        ET.SubElement(component, key).text = value
    engine = ET.SubElement(ET.SubElement(component, "engines"), "engine")
    for key, value in {
        "name": "bo-go-viet-telex", "longname": "Bộ Gõ Việt",
        "description": "Telex / VNI Unicode", "language": "vi", "license": "MIT",
        "author": "Bộ Gõ Việt", "icon": str(DESTINATION / "assets/bo-go-viet.svg"), "layout": "us", "symbol": "VN",
        "setup": f"/usr/bin/python3 {DESTINATION}/preferences.py",
    }.items():
        ET.SubElement(engine, key).text = value
    ET.indent(component)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(component, encoding="unicode") + "\n"


def main():
    parser = argparse.ArgumentParser(description="Cài/gỡ tệp bộ gõ; không tải gói qua mạng")
    parser.add_argument("--uninstall", action="store_true", help="Gỡ tệp bộ gõ khỏi máy")
    parser.add_argument("--print-component", action="store_true", help="Chỉ xem metadata, không cài")
    args = parser.parse_args()
    if args.print_component:
        print(component_xml(), end="")
        return
    if os.geteuid() != 0:
        sys.exit("Cần quyền quản trị để đăng ký với IBus. Chạy: sudo /usr/bin/python3 install.py" + (" --uninstall" if args.uninstall else ""))
    if args.uninstall:
        METADATA.unlink(missing_ok=True)
        DESKTOP.unlink(missing_ok=True)
        if DESTINATION.is_dir():
            for name in FILES:
                (DESTINATION / name).unlink(missing_ok=True)
            shutil.rmtree(DESTINATION / "__pycache__", ignore_errors=True)
            assets = DESTINATION / "assets"
            if assets.is_dir() and not any(assets.iterdir()):
                assets.rmdir()
            if not any(DESTINATION.iterdir()):
                DESTINATION.rmdir()
        print("Đã gỡ tệp Bộ Gõ Việt. Đăng xuất/đăng nhập để IBus làm mới danh sách.")
        print("Gỡ nguồn bàn phím trong tài khoản thường bằng: python3 enable.py --remove")
        return
    try:
        import gi
        gi.require_version("IBus", "1.0")
        gi.require_version("Gtk", "3.0")
    except (ImportError, ValueError):
        sys.exit("Thiếu IBus/GTK. Cài: sudo apt install ibus python3-gi gir1.2-ibus-1.0 gir1.2-gtk-3.0")
    source = Path(__file__).resolve().parent
    missing = [name for name in FILES if not (source / name).is_file()]
    if missing:
        sys.exit("Thiếu tệp: " + ", ".join(missing) + ". Hãy giải nén đầy đủ gói bộ gõ.")
    DESTINATION.mkdir(parents=True, exist_ok=True, mode=0o755)
    for name in FILES:
        (DESTINATION / name).parent.mkdir(parents=True, exist_ok=True)
        if source / name != DESTINATION / name:
            shutil.copyfile(source / name, DESTINATION / name)
        (DESTINATION / name).chmod(0o644)
    METADATA.parent.mkdir(parents=True, exist_ok=True)
    METADATA.write_text(component_xml(), encoding="utf-8")
    METADATA.chmod(0o644)
    DESKTOP.parent.mkdir(parents=True, exist_ok=True)
    DESKTOP.write_text(desktop_entry(), encoding="utf-8")
    DESKTOP.chmod(0o644)
    print("Đã cài tệp Bộ Gõ Việt và đăng ký với IBus.")
    print("Tiếp theo chạy bằng tài khoản thường, KHÔNG sudo: /usr/bin/python3 enable.py")


if __name__ == "__main__":
    main()
