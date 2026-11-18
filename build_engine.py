"""Builds the engine executable the desktop shell runs (dist/engine/AssignmentEngine/AssignmentEngine.exe).

    python build_engine.py

The same bundle contents as the old app (Playwright's driver, the notification and push libraries) minus the Tk window.
It is a console program on purpose: the shell reads its ready line from stdout and hides the console window.
"""
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
NAME = "AssignmentEngine"
sep = ";" if sys.platform == "win32" else ":"


def main():
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--console",
        "--name", NAME,
        "--distpath", str(ROOT / "dist" / "engine"),
        "--workpath", str(ROOT / "build" / "engine"),
        "--specpath", str(ROOT / "build" / "engine"),
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--add-data", f"{ROOT / 'PRIVACY.md'}{sep}docs",
        "--add-data", f"{ROOT / 'CHANGELOG.md'}{sep}docs",
        "--add-data", f"{ROOT / 'SECURITY.md'}{sep}docs",
        "--add-data", f"{ROOT / 'THIRD_PARTY_LICENSES.md'}{sep}docs",
        "--add-data", f"{ROOT / 'LICENSE'}{sep}docs",
        "--collect-all", "playwright",
        "--hidden-import", "winotify",
        "--hidden-import", "pywebpush",
        "--hidden-import", "py_vapid",
        "--hidden-import", "http_ece",
        "--collect-submodules", "qrcode",
        "--collect-all", "nacl",
        "--hidden-import", "pystray._win32",
        "--exclude-module", "customtkinter",
        "--exclude-module", "tkinter.test",
        str(ROOT / "engine.py"),
    ])
    exe = ROOT / "dist" / "engine" / NAME / f"{NAME}.exe"
    if not exe.exists():
        raise SystemExit("Engine build failed: executable not found")
    print(f"Engine: {exe}")


if __name__ == "__main__":
    main()
