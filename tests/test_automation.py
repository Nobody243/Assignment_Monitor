import automation


def test_quote_wraps_paths_with_spaces_and_scripts():
    assert automation._quote([r"C:\Program Files\x\pythonw.exe", r"C:\app\app.py", "--check"]) == \
        '"C:\\Program Files\\x\\pythonw.exe" "C:\\app\\app.py" --check'
    assert automation._quote([r"C:\x\App.exe", "--remind"]) == r"C:\x\App.exe --remind"


def test_task_names_are_namespaced():
    for name in (automation.TASK_DAILY, automation.TASK_HOURLY, automation.TASK_LOGON):
        assert name.startswith("AssignmentMonitor_")
    assert automation.STARTUP_SHORTCUT.endswith(".lnk")
