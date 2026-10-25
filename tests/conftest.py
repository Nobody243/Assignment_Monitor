import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Tests must never touch the real settings or data (neither the installed app's nor the source tree's), never
# show a toast, speak, send a push or an email, call GitHub, or re-register the Windows tasks and shortcuts.
# The data folder is a fresh temporary one, and the AM_ overrides win over anything a settings file says.
_HOME = Path(tempfile.mkdtemp(prefix="am-tests-"))
os.environ["ASSIGNMENT_MONITOR_HOME"] = str(_HOME)
os.environ["LOCALAPPDATA"] = str(_HOME / "localappdata")
for _key in ("ENABLE_WINDOWS_TOAST", "ENABLE_VOICE", "PUSH_ENABLED", "EMAIL_ENABLED", "CALENDAR_ENABLED",
             "CLOUD_ENABLED", "CHECK_UPDATES"):
    os.environ[f"AM_{_key}"] = "False"


import automation  # noqa: E402

# the real functions, for the few tests that exercise them with every subprocess call stubbed
automation.ORIGINALS = {"enable": automation.enable, "refresh_if_outdated": automation.refresh_if_outdated}


@pytest.fixture(autouse=True)
def _no_windows_side_effects(monkeypatch):
    monkeypatch.setattr(automation, "enable", lambda: (True, "tests: automation untouched"))
    monkeypatch.setattr(automation, "disable", lambda: (True, "tests: automation untouched"))
    monkeypatch.setattr(automation, "refresh_if_outdated", lambda: False)
    monkeypatch.setattr(automation, "create_shortcuts", lambda: False)
    monkeypatch.setattr(automation, "set_start_with_windows", lambda want: True)
