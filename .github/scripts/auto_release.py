"""Prepares an automatic release of the desktop app or of the phone app (called by the auto-release workflows).

    python .github/scripts/auto_release.py desktop|phone [--dry-run]

It works out the next version, rewrites the version files and the changelog, writes the release notes to
`release-notes.md`, and prints `version=...`, `tag=...` and `bump=...` lines for the workflow to read. It never runs git
commands that change anything: the workflow commits, tags and pushes.

  * Version: the patch number goes up by one. Put `[minor]` or `[major]` in the subject of any commit since the last
    release to raise that part instead.
  * Notes: the "Unreleased" section of the changelog when it has text (desktop: CHANGELOG.md, phone: mobile/CHANGELOG.md);
    otherwise the commit subjects since the last release, so a release always says what changed.
  * Release commits and merge commits are left out of the notes.
"""
from __future__ import annotations

import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# what each product is made of
PRODUCTS = {
    "desktop": {
        "tag_glob": "v[0-9]*", "tag_prefix": "v", "changelog": "CHANGELOG.md",
        "pathspec": [":!mobile", ":!website", ":!tests", ":!tools", ":!*.md"],
    },
    "phone": {
        "tag_glob": "phone-v[0-9]*", "tag_prefix": "phone-v", "changelog": "mobile/CHANGELOG.md", "pathspec": ["mobile", ":!mobile/*.md"],
    },
}

SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*args: str, root: Path = ROOT) -> str:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True).stdout.strip()


def bump(version: str, kind: str = "patch") -> str:
    m = SEMVER.match(version)
    if not m:
        raise SystemExit(f"not a plain x.y.z version: {version!r}")
    major, minor, patch = (int(x) for x in m.groups())
    if kind == "major":
        return f"{major + 1}.0.0"
    if kind == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def bump_kind(subjects: list[str]) -> str:
    text = "\n".join(subjects).lower()
    return "major" if "[major]" in text else "minor" if "[minor]" in text else "patch"


def clean_subjects(subjects: list[str]) -> list[str]:
    out = []
    for s in subjects:
        low = s.lower()
        if low.startswith(("release ", "merge ", "website: the latest release", "revert \"release")) or "[skip release]" in low:
            continue
        out.append(re.sub(r"\s*\[(minor|major|patch)\]", "", s, flags=re.I).strip())
    return out


def unreleased_text(changelog: str) -> str:
    """The body of the '## Unreleased' section, or ''."""
    m = re.search(r"^## Unreleased[^\n]*\n(.*?)(?=^## |\Z)", changelog, re.S | re.M)
    return m.group(1).strip() if m else ""


def with_release(changelog: str, version: str, today: str, notes: str) -> str:
    """The changelog with the Unreleased section renamed to this release, or a new section added at the top."""
    head = f"## {version} - {today}"
    if re.search(r"^## Unreleased", changelog, re.M):
        return re.sub(r"^## Unreleased[^\n]*", head, changelog, count=1, flags=re.M)
    first = re.search(r"^## ", changelog, re.M)
    section = f"{head}\n\n{notes.strip()}\n\n"
    if first:
        return changelog[: first.start()] + section + changelog[first.start():]
    return (changelog.rstrip() + "\n\n" if changelog.strip() else "# Changelog\n\n") + section


def set_line(path: Path, pattern: str, repl: str, count: int = 1) -> None:
    text = path.read_text(encoding="utf-8")
    new, n = re.subn(pattern, repl, text, count=count, flags=re.M)
    if not n:
        raise SystemExit(f"{path.name}: nothing matched {pattern!r}")
    path.write_bytes(new.encode("utf-8"))


def last_tag(glob: str, root: Path = ROOT) -> str:
    try:
        return git("describe", "--tags", "--match", glob, "--abbrev=0", root=root)
    except subprocess.CalledProcessError:
        return ""


def subjects_since(tag: str, pathspec: list[str], root: Path = ROOT) -> list[str]:
    rng = [f"{tag}..HEAD"] if tag else ["-n", "40"]
    out = git("log", *rng, "--no-merges", "--format=%s", "--", *pathspec, root=root)
    return [s for s in out.splitlines() if s.strip()]


def current_version(product: str, root: Path = ROOT) -> str:
    if product == "desktop":
        m = re.search(r'^APP_VERSION = "([^"]+)"', (root / "config.py").read_text(encoding="utf-8"), re.M)
    else:
        m = re.search(r"^version: (\d+\.\d+\.\d+)", (root / "mobile/pubspec.yaml").read_text(encoding="utf-8"), re.M)
    if not m:
        raise SystemExit("could not read the current version")
    return m.group(1)


def write_versions(product: str, old: str, new: str, root: Path = ROOT) -> None:
    if product == "desktop":
        set_line(root / "config.py", r'^APP_VERSION = "[^"]+"', f'APP_VERSION = "{new}"')
        pkg = root / "desktop/package.json"
        set_line(pkg, rf'^(\s*"version": )"{re.escape(old)}"', rf'\1"{new}"')
        lock = root / "desktop/package-lock.json"
        if lock.exists():
            set_line(lock, rf'^(\s*"version": )"{re.escape(old)}"', rf'\1"{new}"', count=2)
    else:
        text = (root / "mobile/pubspec.yaml").read_text(encoding="utf-8")
        build = int((re.search(r"^version: \d+\.\d+\.\d+\+(\d+)", text, re.M) or [0, 0])[1])
        set_line(root / "mobile/pubspec.yaml", r"^version: .*", f"version: {new}+{build + 1}")
        set_line(root / "mobile/lib/alerts.dart", r"^const appVersion = '[^']+';", f"const appVersion = '{new}';")


def prepare(product: str, root: Path = ROOT, today: str | None = None, dry: bool = False) -> dict[str, str]:
    cfg = PRODUCTS[product]
    old = current_version(product, root)
    tag = last_tag(cfg["tag_glob"], root)
    subjects = subjects_since(tag, cfg["pathspec"], root)
    kind = bump_kind(subjects)
    new = bump(old, kind)
    clog = root / cfg["changelog"]
    text = clog.read_text(encoding="utf-8") if clog.exists() else ""
    notes = unreleased_text(text)
    lines = clean_subjects(subjects)
    if not notes:
        notes = "\n".join(f"- {s}" for s in lines) or "- Maintenance and fixes."
    today = today or dt.date.today().isoformat()
    if not dry:
        write_versions(product, old, new, root)
        clog.parent.mkdir(parents=True, exist_ok=True)
        clog.write_bytes(with_release(text, new, today, notes).encode("utf-8"))
        (root / "release-notes.md").write_bytes((notes.strip() + "\n").encode("utf-8"))
    return {"version": new, "tag": f"{cfg['tag_prefix']}{new}", "bump": kind, "previous": old}


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 1 or args[0] not in PRODUCTS:
        raise SystemExit(__doc__)
    for k, v in prepare(args[0], dry="--dry-run" in sys.argv).items():
        print(f"{k}={v}")
