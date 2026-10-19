import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
# Keep test runs from touching the real settings/data folders.
os.environ.setdefault("LOCALAPPDATA", str(ROOT / "build" / "test-localappdata"))
