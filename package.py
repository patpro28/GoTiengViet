#!/usr/bin/python3
"""Bundle the Linux app and tests without the macOS reference checkout."""
import hashlib
from pathlib import Path
import tarfile
from install import FILES
from settings import VERSION


def main():
    root = Path(__file__).resolve().parent
    output = root / "dist"
    output.mkdir(exist_ok=True)
    name = f"bo-go-viet-{VERSION}"
    archive = output / f"{name}.tar.gz"
    files = (*FILES, "package.py", "test_telex.py", "test_engine.py", "test_features.py", "test_install.py", "integration_check.py", "ui_check.py")
    with tarfile.open(archive, "w:gz") as bundle:
        for file in files:
            bundle.add(root / file, arcname=f"{name}/{file}", recursive=False)
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / f"{name}.sha256").write_text(f"{checksum}  {archive.name}\n", encoding="ascii")
    print(archive)


if __name__ == "__main__":
    main()
