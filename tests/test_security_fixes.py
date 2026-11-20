"""Regression tests for the findings GitHub's code scanning (CodeQL) raised against the engine and the settings file:
uncontrolled data in a file path (the upload), an echoed request header (CORS origin), clear-text storage of the password
and secrets in a log line."""
import logging
import os
import sys

import pytest

import config
import engine


class FakeHandler:
    """Just enough of the request handler to test the origin check on its own."""
    _origin_ok = engine.Handler._origin_ok

    def __init__(self, origin, allowed):
        self.headers = {"Origin": origin} if origin is not None else {}
        self.server = type("S", (), {"allowed_origins": allowed})()


# ---------------------------------------------------------------------------------------------- the CORS origin
def test_an_allowed_origin_is_answered_with_our_own_copy_of_it():
    allowed = ("http://localhost:5173", "app://assignment-monitor")
    handler = FakeHandler("http://localhost:5173", allowed)
    got = handler._origin_ok()
    assert got == "http://localhost:5173" and got is allowed[0]      # the server's string, not the header's


@pytest.mark.parametrize("origin", [None, "", "http://evil.example", "http://localhost:5173\r\nSet-Cookie: x=1", "http://localhost:5173 ", "HTTP://LOCALHOST:5173"])
def test_anything_else_gets_no_cors_header(origin):
    assert FakeHandler(origin, ("http://localhost:5173",))._origin_ok() is None


# ---------------------------------------------------------------------------------------------- the upload path
@pytest.mark.parametrize("raw, expected", [
    ("report.pdf", "report.pdf"),
    ("../../Windows/System32/evil.pdf", "evil.pdf"),
    ("..\\..\\evil.pdf", "evil.pdf"),
    ("C:\\Users\\x\\secret.pdf", "secret.pdf"),
    ("a/b/c.pdf", "c.pdf"),
    ("na\x00me\r\n.pdf", "na_me__.pdf"),
    ("..", "upload.pdf"),
    ("...", "upload.pdf"),
    ("   ", "upload.pdf"),
    ("", "upload.pdf"),
    (None, "upload.pdf"),
    ("hello <world> | *.pdf", "hello _world_ _ _.pdf"),
    ("nul", "_nul"),
    ("CON.pdf", "_CON.pdf"),
    ("com1.txt", "_com1.txt"),
    ("console.pdf", "console.pdf"),
    ("اسائنمنٹ حل.pdf", "اسائنمنٹ حل.pdf"),                           # other scripts are kept
])
def test_upload_names_are_reduced_to_plain_characters(raw, expected):
    assert engine.safe_upload_name(raw) == expected


def test_a_long_name_is_cut():
    assert len(engine.safe_upload_name("x" * 1000 + ".pdf")) <= engine.MAX_FILENAME


def test_the_upload_file_always_lands_inside_its_own_private_folder():
    made = []
    try:
        for raw in ["a.pdf", "../x.pdf", "..\\..\\y.pdf", "C:/z.pdf", "..", "nul", "con.pdf"]:
            path = engine.private_upload_path(raw)
            folder = os.path.dirname(path)
            made.append(folder)
            assert os.path.isdir(folder) and os.path.dirname(os.path.realpath(path)) == os.path.realpath(folder)
            assert os.path.basename(folder).startswith("am-upload-")
            assert not os.path.exists(path)                       # only the name is made; the caller creates the file
    finally:
        for folder in made:
            os.rmdir(folder)


def test_the_private_folder_is_not_shared_between_uploads():
    a, b = engine.private_upload_path("same.pdf"), engine.private_upload_path("same.pdf")
    try:
        assert os.path.dirname(a) != os.path.dirname(b)
    finally:
        os.rmdir(os.path.dirname(a))
        os.rmdir(os.path.dirname(b))


# ---------------------------------------------------------------------------------------------- the settings file
@pytest.fixture
def env_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "ENV_PATH", tmp_path / "settings.env")
    monkeypatch.setattr(config, "IN_CLOUD", False)
    return tmp_path / "settings.env"


def test_the_password_is_never_written_as_plain_text_even_if_encryption_fails(env_file, monkeypatch, caplog):
    class Broken:
        @staticmethod
        def encrypt_secret(value):
            raise OSError("DPAPI said no: " + value)             # an error message that would leak the value if logged

    monkeypatch.setitem(sys.modules, "secure_store", Broken)
    secret = "hunter2-very-secret"
    with caplog.at_level(logging.WARNING, logger="bahria.config"):
        config.save_env({"ENROLLMENT": "01-000000-000", "PASSWORD": secret})
    text = env_file.read_text(encoding="utf-8")
    assert secret not in text and "PASSWORD=" not in text
    assert secret not in caplog.text and "could not be encrypted" in caplog.text     # said, without the value or the error text


def test_a_secret_that_cannot_be_encrypted_is_dropped_not_stored_and_not_logged(env_file, monkeypatch, caplog):
    class Broken:
        @staticmethod
        def encrypt_secret(value):
            raise OSError("boom " + value)

    monkeypatch.setitem(sys.modules, "secure_store", Broken)
    key = config._SECRET_KEYS[1]
    with caplog.at_level(logging.WARNING, logger="bahria.config"):
        config.save_env({"ENROLLMENT": "01-000000-000", key: "app-password-123"})
    assert "app-password-123" not in env_file.read_text(encoding="utf-8")
    assert "app-password-123" not in caplog.text


def test_a_stored_secret_that_cannot_be_read_is_logged_without_its_name_or_the_error_text(env_file, monkeypatch, caplog):
    class Broken:
        @staticmethod
        def decrypt_secret(blob):
            raise ValueError("leaky detail " + blob)

    monkeypatch.setitem(sys.modules, "secure_store", Broken)
    key = config._SECRET_KEYS[1]
    env_file.write_text(f"ENROLLMENT=01-000000-000\n{key}_ENC=c2VjcmV0\nPASSWORD_ENC=c2VjcmV0\n", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="bahria.config"):
        config.load_env()
    assert "leaky detail" not in caplog.text and key not in caplog.text and "c2VjcmV0" not in caplog.text
    assert "could not be decrypted" in caplog.text
