"""Turns the failures in a pytest log into GitHub annotations (::error lines), so the reason for a red run is visible on
the run's summary page and through the public API, without opening the full log.

    python .github/scripts/annotate_failures.py pytest.log
"""
import re
import sys
from pathlib import Path


def main(path: str) -> None:
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    shown = 0
    for line in lines:
        if shown >= 25:
            break
        if re.match(r"^(FAILED|ERROR) ", line) or re.match(r"^E\s{2,}\S", line):
            text = line.strip().replace("%", "%25").replace("\r", "").replace("\n", "%0A")[:400]
            print(f"::error title=pytest::{text}")
            shown += 1
    if shown == 0:
        tail = " | ".join(x.strip() for x in lines[-6:] if x.strip())[:400]
        print(f"::error title=pytest::no FAILED lines found; log ends: {tail}")


if __name__ == "__main__":
    main(sys.argv[1])
