"""Writes summary.json for the phone app's fixture from the fictional seed data:  python tools/make_summary.py <output file>"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main(out: Path) -> None:
    home = tempfile.mkdtemp(prefix="am-summary-")
    os.environ["ASSIGNMENT_MONITOR_HOME"] = home
    import tools.seed_demo_data as seed
    seed.seed(Path(home))
    import engine
    import summary
    data = summary.build(engine.build_state())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"wrote {out} ({len(data['assignments'])} assignments, {len(data['attendance'])} courses)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(Path(sys.argv[1]))
