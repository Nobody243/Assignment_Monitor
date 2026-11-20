"""Looks every package in mobile/pubspec.lock up in the OSV vulnerability database (osv.dev, ecosystem "Pub").

    python tools/dart_osv_check.py

Only package names and versions are sent. Exits 1 if any known vulnerability applies to a locked version, so CI can stop a
release that ships one. (The Dart tool has no `pub audit` yet; this is the equivalent.)
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

LOCK = Path(__file__).resolve().parent.parent / "mobile" / "pubspec.lock"


def packages() -> list:
    out, name = [], None
    for line in LOCK.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^  (\S+):$", line)
        if m:
            name = m.group(1)
            continue
        v = re.match(r'^    version: "?([^"\s]+)"?$', line)
        if v and name:
            out.append((name, v.group(1)))
    return out


def main() -> int:
    pkgs = packages()
    body = json.dumps({"queries": [{"package": {"name": n, "ecosystem": "Pub"}, "version": v} for n, v in pkgs]}).encode()
    req = urllib.request.Request("https://api.osv.dev/v1/querybatch", data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:  # nosec B310 - fixed https URL
        results = json.load(r)["results"]
    bad = [(n, v, [x["id"] for x in res.get("vulns", [])]) for (n, v), res in zip(pkgs, results, strict=True) if res.get("vulns")]
    print(f"checked {len(pkgs)} locked packages against osv.dev")
    for n, v, ids in bad:
        print(f"  VULNERABLE {n} {v}: {', '.join(ids)}")
    if not bad:
        print("  none known")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
