"""The automatic-release script: version arithmetic, changelog rewriting, note choice, and a full run in a throw-away repo."""
from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / ".github" / "scripts" / "auto_release.py"
spec = importlib.util.spec_from_file_location("auto_release", SCRIPT)
ar = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ar)


def test_bump_parts():
    assert ar.bump("1.9.6") == "1.9.7"
    assert ar.bump("1.9.6", "minor") == "1.10.0"
    assert ar.bump("1.9.6", "major") == "2.0.0"
    with pytest.raises(SystemExit):
        ar.bump("1.9")


def test_bump_kind_from_commit_subjects():
    assert ar.bump_kind(["Fix a thing"]) == "patch"
    assert ar.bump_kind(["Fix a thing", "New page [minor]"]) == "minor"
    assert ar.bump_kind(["[minor] x", "Rewrite [major]"]) == "major"


def test_release_and_merge_commits_are_left_out_of_the_notes():
    got = ar.clean_subjects(["Release 1.9.6: x", "Merge branch 'a'", "Website: the latest release is v1.9.6 (by the release build)",
                             "Fix the thing [minor]", "Docs [skip release]"])
    assert got == ["Fix the thing"]


def test_unreleased_section_is_found_and_renamed():
    text = "# Changelog\n\n## Unreleased\n\n- New thing.\n\n## 1.0.0 - 2026-01-01\n\n- Old.\n"
    assert ar.unreleased_text(text) == "- New thing."
    out = ar.with_release(text, "1.0.1", "2026-02-02", "- New thing.")
    assert "## 1.0.1 - 2026-02-02" in out and "Unreleased" not in out and out.index("1.0.1") < out.index("1.0.0")


def test_a_section_is_added_when_there_is_no_unreleased_one():
    out = ar.with_release("# Changelog\n\n## 1.0.0 - 2026-01-01\n\n- Old.\n", "1.0.1", "2026-02-02", "- Fix.")
    assert out.index("## 1.0.1 - 2026-02-02") < out.index("## 1.0.0")
    assert ar.with_release("", "1.0.1", "2026-02-02", "- Fix.").startswith("# Changelog")


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t", *args], cwd=root, check=True, capture_output=True)


def make_repo(tmp: Path) -> Path:
    (tmp / "desktop").mkdir(parents=True)
    (tmp / "mobile/lib").mkdir(parents=True)
    (tmp / "config.py").write_text('APP_VERSION = "1.2.3"\n', encoding="utf-8")
    (tmp / "desktop/package.json").write_text('{\n  "name": "x",\n  "version": "1.2.3"\n}\n', encoding="utf-8")
    lock = '{\n  "version": "1.2.3",\n  "packages": {\n    "": {\n      "version": "1.2.3"\n    }\n  }\n}\n'
    (tmp / "desktop/package-lock.json").write_text(lock, encoding="utf-8")
    (tmp / "mobile/pubspec.yaml").write_text("name: m\nversion: 1.0.4+7\n", encoding="utf-8")
    (tmp / "mobile/lib/alerts.dart").write_text("const appVersion = '1.0.4';   // keep in step\n", encoding="utf-8")
    (tmp / "CHANGELOG.md").write_text("# Changelog\n\n## 1.2.3 - 2026-01-01\n\n- Old.\n", encoding="utf-8")
    git(tmp, "init", "-q")
    git(tmp, "add", "-A")
    git(tmp, "commit", "-q", "-m", "start")
    git(tmp, "tag", "v1.2.3")
    git(tmp, "tag", "phone-v1.0.4")
    return tmp


def test_desktop_release_end_to_end(tmp_path):
    root = make_repo(tmp_path)
    (root / "config.py").write_text('APP_VERSION = "1.2.3"\nX = 1\n', encoding="utf-8")
    git(root, "commit", "-qam", "Make the thing faster")
    (root / "mobile/lib/a.dart").write_text("//\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Phone only change")
    out = ar.prepare("desktop", root, today="2026-03-04")
    assert out == {"version": "1.2.4", "tag": "v1.2.4", "bump": "patch", "previous": "1.2.3"}
    assert 'APP_VERSION = "1.2.4"' in (root / "config.py").read_text(encoding="utf-8")
    assert '"version": "1.2.4"' in (root / "desktop/package.json").read_text(encoding="utf-8")
    lock = (root / "desktop/package-lock.json").read_text(encoding="utf-8")
    assert lock.count('"version": "1.2.4"') == 2 and "1.2.3" not in lock
    log = (root / "CHANGELOG.md").read_text(encoding="utf-8")
    assert "## 1.2.4 - 2026-03-04" in log and "- Make the thing faster" in log
    notes = (root / "release-notes.md").read_text(encoding="utf-8")
    assert "Make the thing faster" in notes and "Phone only change" not in notes, "the phone commit belongs to the phone release"


def test_phone_release_end_to_end(tmp_path):
    root = make_repo(tmp_path)
    (root / "mobile/lib/a.dart").write_text("//\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-qm", "Bigger tap targets [minor]")
    (root / "config.py").write_text('APP_VERSION = "1.2.3"\nY = 1\n', encoding="utf-8")
    git(root, "commit", "-qam", "Desktop only change")
    out = ar.prepare("phone", root, today="2026-03-04")
    assert out["version"] == "1.1.0" and out["tag"] == "phone-v1.1.0" and out["bump"] == "minor"
    assert "version: 1.1.0+8" in (root / "mobile/pubspec.yaml").read_text(encoding="utf-8")
    assert "const appVersion = '1.1.0';" in (root / "mobile/lib/alerts.dart").read_text(encoding="utf-8")
    notes = (root / "release-notes.md").read_text(encoding="utf-8")
    assert "Bigger tap targets" in notes and "Desktop only" not in notes and "[minor]" not in notes
    assert "## 1.1.0 - 2026-03-04" in (root / "mobile/CHANGELOG.md").read_text(encoding="utf-8")


def test_unreleased_notes_win_over_commit_subjects(tmp_path):
    root = make_repo(tmp_path)
    text = "# Changelog\n\n## Unreleased\n\n- Hand-written note.\n\n## 1.2.3 - 2026-01-01\n\n- Old.\n"
    (root / "CHANGELOG.md").write_text(text, encoding="utf-8")
    (root / "config.py").write_text('APP_VERSION = "1.2.3"\nZ = 1\n', encoding="utf-8")
    git(root, "commit", "-qam", "Some commit")
    ar.prepare("desktop", root, today="2026-03-04")
    assert (root / "release-notes.md").read_text(encoding="utf-8").strip() == "- Hand-written note."
    assert "Some commit" not in (root / "CHANGELOG.md").read_text(encoding="utf-8")


def test_dry_run_changes_nothing(tmp_path):
    root = make_repo(tmp_path)
    (root / "config.py").write_text('APP_VERSION = "1.2.3"\nQ = 1\n', encoding="utf-8")
    git(root, "commit", "-qam", "x")
    before = (root / "config.py").read_text(encoding="utf-8")
    assert ar.prepare("desktop", root, dry=True)["version"] == "1.2.4"
    assert (root / "config.py").read_text(encoding="utf-8") == before and not (root / "release-notes.md").exists()
