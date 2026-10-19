"""Builds the Windows app: PyInstaller folder build, portable zip, and (when Inno Setup
is available) the installer.

    pip install -r requirements.txt pyinstaller
    python build.py

Outputs in dist/:
    AssignmentMonitor/                   the built app folder
    AssignmentMonitor-portable.zip       zip of that folder
    AssignmentMonitor-Setup.exe          installer (needs Inno Setup 6, ISCC.exe)
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).resolve().parent
NAME = "AssignmentMonitor"
DIST = ROOT / "dist"
sys.path.insert(0, str(ROOT))
from config import APP_VERSION  # noqa: E402


def find_iscc():
    candidates = [
        os.environ.get("ISCC", ""),
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        str(Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe"),
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return shutil.which("iscc")


def main():
    sep = ";" if sys.platform == "win32" else ":"
    PyInstaller.__main__.run([
        "--noconfirm", "--clean", "--windowed",
        "--name", NAME,
        "--icon", str(ROOT / "assets" / "icon.ico"),
        "--add-data", f"{ROOT / 'assets'}{sep}assets",
        "--add-data", f"{ROOT / 'PRIVACY.md'}{sep}docs",
        "--add-data", f"{ROOT / 'SECURITY.md'}{sep}docs",
        "--add-data", f"{ROOT / 'THIRD_PARTY_LICENSES.md'}{sep}docs",
        "--add-data", f"{ROOT / 'LICENSE'}{sep}docs",
        "--collect-all", "customtkinter",
        "--collect-all", "playwright",          # bundles the Node driver: no Python or Node needed
        "--hidden-import", "winotify",
        "--hidden-import", "pystray._win32",
        "--exclude-module", "tkinter.test",
        str(ROOT / "app.py"),
    ])
    out_dir = DIST / NAME
    if not (out_dir / f"{NAME}.exe").exists():
        raise SystemExit("Build failed: executable not found")

    zip_base = DIST / f"{NAME}-portable"
    if zip_base.with_suffix(".zip").exists():
        zip_base.with_suffix(".zip").unlink()
    shutil.make_archive(str(zip_base), "zip", root_dir=DIST, base_dir=NAME)
    print(f"\nPortable zip: {zip_base}.zip ({zip_base.with_suffix('.zip').stat().st_size / 1_048_576:.0f} MB)")

    iscc = find_iscc()
    if not iscc:
        print("Inno Setup (ISCC.exe) not found: installer skipped. Install it from https://jrsoftware.org/isinfo.php")
        return
    r = subprocess.run([iscc, "/Q", f"/DAppVersion={APP_VERSION}", f"/DSourceDir={out_dir}",
                        str(ROOT / "installer.iss")], cwd=ROOT)
    if r.returncode != 0:
        raise SystemExit("Installer build failed")
    setup = DIST / f"{NAME}-Setup.exe"
    print(f"Installer:    {setup} ({setup.stat().st_size / 1_048_576:.0f} MB)")


if __name__ == "__main__":
    main()
