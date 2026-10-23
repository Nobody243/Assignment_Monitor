import sys
from pathlib import Path
from urllib.parse import unquote

import crash
from config import APP_VERSION


def _info():
    try:
        raise ValueError("boom in " + str(Path.home() / "somewhere"))
    except ValueError:
        return sys.exc_info()


def test_describe_has_type_message_and_frames_without_the_home_directory():
    d = crash.describe(*_info())
    assert d.startswith("ValueError: boom in")
    assert str(Path.home()) not in d
    assert "~" in d
    assert "test_crash.py" in d and "_info" in d


def test_report_url_is_a_prefilled_issue():
    url = crash.report_url("ValueError: boom\n  at x.py:1 in f", where="a window callback")
    assert url.startswith(crash.ISSUES_URL + "?title=")
    body = unquote(url.split("&body=", 1)[1])
    assert APP_VERSION in body and "ValueError: boom" in body and "a window callback" in body
    assert "Crash%3A%20ValueError" in url


def test_should_show_throttles_the_same_error():
    crash._last.update(sig=None, at=0.0)
    assert crash.should_show("A: one\n  at x")
    assert not crash.should_show("A: one\n  at y")
    assert crash.should_show("B: other")


def test_install_routes_callback_errors_to_the_dialog():
    shown = []

    class FakeApp:
        def after(self, _ms, fn, *args):
            fn(*args)
    app = FakeApp()
    crash._last.update(sig=None, at=0.0)
    old_hook = sys.excepthook
    try:
        crash.install(app, shown.append)
        app.report_callback_exception(*_info())
    finally:
        sys.excepthook = old_hook
    assert len(shown) == 1 and shown[0].startswith("ValueError: boom in")
