"""Line coverage per file from `flutter test --coverage` (mobile/coverage/lcov.info).

    cd mobile && flutter test --coverage && cd .. && python tools/dart_coverage.py [--min 60]

Exits 1 when the total is under --min, so CI can hold a floor.
"""
import sys
from pathlib import Path

LCOV = Path(__file__).resolve().parent.parent / "mobile" / "coverage" / "lcov.info"


def main() -> int:
    floor = float(sys.argv[sys.argv.index("--min") + 1]) if "--min" in sys.argv else 0.0
    files, cur = {}, None
    for line in LCOV.read_text(encoding="utf-8").splitlines():
        if line.startswith("SF:"):
            cur = line[3:].replace("\\", "/")
            files[cur] = [0, 0]
        elif line.startswith("DA:") and cur:
            hits = int(line[3:].split(",")[1])
            files[cur][1] += 1
            files[cur][0] += 1 if hits > 0 else 0
    hit = sum(h for h, _ in files.values())
    total = sum(t for _, t in files.values())
    for f, (h, t) in sorted(files.items(), key=lambda kv: kv[1][0] / max(kv[1][1], 1)):
        print(f"{100 * h / max(t, 1):5.1f}%  {h:4d}/{t:4d}  {f.split('lib/')[-1]}")
    pct = 100 * hit / max(total, 1)
    print(f"TOTAL {pct:.1f}%  {hit}/{total}")
    return 0 if pct >= floor else 1


if __name__ == "__main__":
    sys.exit(main())
