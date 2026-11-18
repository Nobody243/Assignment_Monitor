"""Builds the desktop app end to end: interface -> engine executable -> shell folder -> portable zip -> installer.

    pip install -r requirements-dev.txt pyinstaller
    python build_desktop.py

Outputs in dist/ (the same names the update check and the website already use):
    shell/AssignmentMonitor/                 the app folder (AssignmentMonitor.exe + resources/{ui,engine,assets})
    AssignmentMonitor-portable.zip           zip of that folder
    AssignmentMonitor-Setup.exe              installer (needs Inno Setup 6, ISCC.exe)
    AssignmentMonitor-Setup.exe.sha256       the checksum the in-app updater verifies before it runs the installer
"""
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
NAME = "AssignmentMonitor"
sys.path.insert(0, str(ROOT))
from build import find_iscc  # noqa: E402
from config import APP_VERSION  # noqa: E402

NPM = shutil.which("npm") or "npm"


def run(cmd, cwd=ROOT):
    print("\n$", " ".join(str(c) for c in cmd))
    subprocess.run([str(c) for c in cmd], cwd=cwd, check=True)


def main():
    run([NPM, "ci"], ROOT / "ui")
    run([NPM, "run", "build"], ROOT / "ui")
    run([sys.executable, "build_engine.py"])
    run([NPM, "ci"], ROOT / "desktop")
    run([NPM, "run", "package"], ROOT / "desktop")

    app_dir = DIST / "shell" / NAME
    if not (app_dir / f"{NAME}.exe").exists():
        raise SystemExit("Build failed: AssignmentMonitor.exe not found")

    zip_base = DIST / f"{NAME}-portable"
    zip_base.with_suffix(".zip").unlink(missing_ok=True)
    shutil.make_archive(str(zip_base), "zip", root_dir=app_dir.parent, base_dir=NAME)
    print(f"\nPortable zip: {zip_base}.zip ({zip_base.with_suffix('.zip').stat().st_size / 1_048_576:.0f} MB)")

    iscc = find_iscc()
    if not iscc:
        print("Inno Setup (ISCC.exe) not found: installer skipped. Install it from https://jrsoftware.org/isinfo.php")
        return
    run([iscc, "/Q", f"/DAppVersion={APP_VERSION}", f"/DSourceDir={app_dir}", ROOT / "installer.iss"])
    setup = DIST / f"{NAME}-Setup.exe"
    digest = hashlib.sha256(setup.read_bytes()).hexdigest()
    Path(f"{setup}.sha256").write_text(f"{digest}  {setup.name}\n", encoding="ascii")
    print(f"Installer:    {setup} ({setup.stat().st_size / 1_048_576:.0f} MB)\nSHA-256:      {digest}")


if __name__ == "__main__":
    main()
