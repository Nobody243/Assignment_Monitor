"""Builds the standalone Windows app with PyInstaller and zips it for distribution.

    pip install -r requirements.txt pyinstaller
    python build.py

Output: dist/BahriaLMSMonitor/BahriaLMSMonitor.exe and dist/BahriaLMSMonitor-windows.zip
"""
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
NAME = "BahriaLMSMonitor"
DIST = ROOT / "dist"


def main():
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--windowed",
        "--name", NAME,
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--add-data", f"{ROOT / 'assets'}{';' if sys.platform == 'win32' else ':'}assets",
        "--collect-all", "customtkinter",
        "--collect-all", "playwright",          # bundles the Node driver so no Python/Node is needed
        "--hidden-import", "winotify",
        "--exclude-module", "tkinter.test",
        str(ROOT / "app.py"),
    ])
    out_dir = DIST / NAME
    if not (out_dir / f"{NAME}.exe").exists():
        raise SystemExit("Build failed: executable not found")
    zip_base = DIST / f"{NAME}-windows"
    if zip_base.with_suffix(".zip").exists():
        zip_base.with_suffix(".zip").unlink()
    shutil.make_archive(str(zip_base), "zip", root_dir=DIST, base_dir=NAME)
    size_mb = zip_base.with_suffix(".zip").stat().st_size / 1_048_576
    print(f"\nBuilt {out_dir / (NAME + '.exe')}\nZipped {zip_base}.zip ({size_mb:.0f} MB)")


if __name__ == "__main__":
    main()
