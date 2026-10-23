import automation


def test_quote_wraps_paths_with_spaces_and_scripts():
    assert automation._quote([r"C:\Program Files\x\pythonw.exe", r"C:\app\app.py", "--check"]) == \
        '"C:\\Program Files\\x\\pythonw.exe" "C:\\app\\app.py" --check'
    assert automation._quote([r"C:\x\App.exe", "--remind"]) == r"C:\x\App.exe --remind"


def test_task_names_are_namespaced():
    for name in (automation.TASK_DAILY, automation.TASK_HOURLY, automation.TASK_LOGON):
        assert name.startswith("AssignmentMonitor_")
    assert automation.STARTUP_SHORTCUT.endswith(".lnk")


def test_task_xml_has_the_laptop_settings():
    """The daily task wakes the PC, runs on battery, runs a missed start late and retries; the hourly one does not
    wake the PC. Paths with spaces and ampersands survive as XML."""
    import xml.etree.ElementTree as ET
    cmd = [r"C:\Program Files\A & B\AssignmentMonitor.exe", "--check"]
    daily = automation._task_xml(cmd, automation._daily_trigger(), wake=True, limit="PT30M", restart=True)
    root = ET.fromstring(daily.split("?>", 1)[1])
    ns = {"t": "http://schemas.microsoft.com/windows/2004/02/mit/task"}
    st = root.find("t:Settings", ns)
    assert st.find("t:WakeToRun", ns).text == "true"
    assert st.find("t:DisallowStartIfOnBatteries", ns).text == "false"
    assert st.find("t:StopIfGoingOnBatteries", ns).text == "false"
    assert st.find("t:StartWhenAvailable", ns).text == "true"
    assert st.find("t:RestartOnFailure/t:Count", ns).text == "3"
    assert root.find("t:Actions/t:Exec/t:Command", ns).text == cmd[0]
    assert root.find("t:Actions/t:Exec/t:Arguments", ns).text == "--check"
    assert root.find("t:Triggers/t:CalendarTrigger/t:StartBoundary", ns).text.endswith("T19:00:00")
    hourly = automation._task_xml(cmd, automation._hourly_trigger(), wake=False, limit="PT5M", restart=False)
    root = ET.fromstring(hourly.split("?>", 1)[1])
    assert root.find("t:Settings/t:WakeToRun", ns).text == "false"
    assert root.find("t:Settings/t:RestartOnFailure", ns) is None
    assert root.find("t:Triggers/t:TimeTrigger/t:Repetition/t:Interval", ns).text == "PT1H"
    assert automation.TASK_MARK in daily
