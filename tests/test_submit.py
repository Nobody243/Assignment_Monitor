import lms_scraper as L


def test_upload_name_drops_special_symbols_and_lowercases_extension():
    assert L.submission_upload_name(r"C:\x\My#Report $final (v2).PDF") == "MyReport final (v2).pdf"
    assert L.submission_upload_name("###.zip") == "submission.zip"


def test_file_checks(tmp_path):
    ok = tmp_path / "a.pdf"
    ok.write_bytes(b"x" * 10)
    assert L.check_submission_file(ok) == ""
    assert "does not exist" in L.check_submission_file(tmp_path / "none.pdf")
    exe = tmp_path / "a.exe"
    exe.write_bytes(b"x")
    assert "accepts only" in L.check_submission_file(exe)
    empty = tmp_path / "e.docx"
    empty.write_bytes(b"")
    assert "empty" in L.check_submission_file(empty)
    big = tmp_path / "b.zip"
    big.write_bytes(b"x" * (L.SUBMIT_MAX_BYTES + 1))
    assert "15 MB" in L.check_submission_file(big)
    edge = tmp_path / "c.zip"
    edge.write_bytes(b"x" * L.SUBMIT_MAX_BYTES)
    assert L.check_submission_file(edge) == ""
