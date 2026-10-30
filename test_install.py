"""Installer checks use temporary destinations; no system paths are written."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import gi

gi.require_version("IBus", "1.0")
from gi.repository import IBus
import install


class InstallTests(unittest.TestCase):
    def test_xml_parses_with_real_ibus_library(self):
        with tempfile.TemporaryDirectory(prefix="bgv-xml-") as directory:
            metadata = Path(directory) / "engine.xml"
            metadata.write_text(install.component_xml(), encoding="utf-8")
            component = IBus.Component.new_from_file(str(metadata))
            self.assertEqual(component.get_name(), "org.freedesktop.IBus.BoGoViet")
            self.assertEqual(component.get_engines()[0].get_name(), "bo-go-viet-telex")
            self.assertEqual(component.get_engines()[0].get_layout(), "us")

    def test_install_and_remove_only_owned_files_in_temporary_directory(self):
        with tempfile.TemporaryDirectory(prefix="bgv-install-") as directory:
            destination = Path(directory) / "code"
            metadata = Path(directory) / "components/bo-go-viet.xml"
            desktop = Path(directory) / "applications/bo-go-viet.desktop"
            with patch.object(install, "DESTINATION", destination), patch.object(install, "METADATA", metadata), patch.object(install, "DESKTOP", desktop), patch.object(install.os, "geteuid", return_value=0), contextlib.redirect_stdout(io.StringIO()):
                with patch("sys.argv", ["install.py"]):
                    install.main()
                self.assertTrue(metadata.is_file())
                self.assertIn(str(destination / "preferences.py"), desktop.read_text())
                for name in install.FILES:
                    self.assertTrue((destination / name).is_file())
                    self.assertEqual((destination / name).stat().st_mode & 0o777, 0o644)
                unrelated = destination / "personal-note.txt"
                unrelated.write_text("preserve me")
                with patch("sys.argv", ["install.py", "--uninstall"]):
                    install.main()
                self.assertFalse(metadata.exists())
                self.assertFalse(desktop.exists())
                self.assertEqual(unrelated.read_text(), "preserve me")
                self.assertEqual(list(destination.iterdir()), [unrelated])

    def test_non_admin_install_exits_before_writing(self):
        with patch.object(install.os, "geteuid", return_value=1000), patch("sys.argv", ["install.py"]):
            with self.assertRaises(SystemExit):
                install.main()


if __name__ == "__main__":
    unittest.main(verbosity=2)
