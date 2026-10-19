# Assignment Monitor

**for Bahria University LMS**

A Windows app that keeps an eye on your LMS assignments so you don't have to. Install it, sign in once, and it quietly does the rest.

- Dashboard of what's pending, due today, due this week, extended, overdue and submitted
- Notices when a teacher **extends a deadline**, even though the portal squashes the old and new dates together
- **Daily check at 7 PM** and a catch-up check when you sign in to Windows
- **Hourly voice reminder** on the day an unsubmitted assignment is due
- Lives in the **system tray**, can start with Windows, dark and light themes

## Install

1. Download **`AssignmentMonitor-Setup.exe`** from the [latest release](https://github.com/Nobody243/Assignment_Monitor/releases/latest).
2. Run it. It installs for your user account only (no administrator password) and adds a Start Menu and Desktop icon.
3. Open Assignment Monitor, enter your enrollment number, CMS password and campus, leave "Run automatically" ticked, and click **Connect & start monitoring**.

That's it. The app verifies the sign-in, reads your assignments and registers the background checks.

Prefer no installer? `AssignmentMonitor-portable.zip` from the same release runs from any folder.

> Windows SmartScreen may warn the first time because the app isn't code-signed. Click **More info**, then **Run anyway**.

**Requirements:** Windows 10 or 11. Google Chrome is used if installed; otherwise a browser engine is downloaded once automatically.

## Using it

| Screen | What it does |
| --- | --- |
| **Dashboard** | "Up next" card, counters, needs-attention list sorted by deadline, per-course progress. Click any counter or course to filter. |
| **Assignments** | Full list with filters, course picker and search. Shows extension history and marks. |
| **Settings** | Account and campus, theme, tray and start-with-Windows options, voice and notification preferences, background automation, switch account. |
| **Activity** | Log of every sync and reminder, including the scheduled background runs. |

**Tray:** closing the window keeps the app in the system tray (you can turn this off in Settings). Right-click the tray icon to open, sync now, or quit. "Start with Windows" opens it minimized to the tray at sign-in.

**Background automation** registers three scheduled tasks for your user account:

| Task | When | What |
| --- | --- | --- |
| `AssignmentMonitor_DailyCheck` | Daily 19:00 | Sync + notifications |
| `AssignmentMonitor_LogonCheck` | 2 min after sign-in | Catch-up sync if the PC was off at 19:00 |
| `AssignmentMonitor_HourlyReminder` | Every hour | Voice + toast while something unsubmitted is due today |

These run even when the app window is closed. Turn them off any time from Settings. Uninstalling removes them too.

**Updating:** Settings → "Check for updates" opens the Releases page. Install the new Setup over the old one; your sign-in and data are kept.

## Privacy

- Your password is encrypted with Windows Data Protection (DPAPI) for your user account and stored in `%LOCALAPPDATA%\Assignment Monitor\settings.env`. It is only ever sent to `cms.bahria.edu.pk` when signing in.
- Assignment data, logs and the browser profile stay in that same local folder. Nothing is sent anywhere else.

## Run from source

```bash
git clone https://github.com/Nobody243/Assignment_Monitor.git
cd Assignment_Monitor
pip install -r requirements.txt
python app.py
```

Command-line modes (also what the scheduled tasks call):

```
python app.py --check                sync and notify
python app.py --check -q             sync without notifications
python app.py --remind               hourly same-day reminder
python app.py --status               print saved assignments
python app.py --test-alert           test notification and voice
python app.py --tray                 start minimized to the tray
python app.py --setup                open the sign-in screen (switch account)
python app.py --enable-automation    register the background tasks
python app.py --disable-automation   remove them
```

When running from source, data lives in the project folder (`.env`, `data/`, `chrome_profile/`), all git-ignored.

## Build

```bash
pip install -r requirements.txt pyinstaller
python build.py
```

Produces `dist/AssignmentMonitor-portable.zip` and, if [Inno Setup 6](https://jrsoftware.org/isinfo.php) is installed, `dist/AssignmentMonitor-Setup.exe`. Pushing a tag like `v2.1.0` runs the same build on GitHub Actions and attaches both files to a release.

## How it works

1. Playwright drives Chrome headlessly: sign in at `cms.bahria.edu.pk`, follow the CMS → LMS single sign-on, open `Student/Assignments.php`.
2. For every course in the semester dropdown it reads the assignments table. The portal concatenates an extended deadline with the original (`4 October 2026 - 11:50 am13 September 2026-11:55 am`); the parser splits those apart.
3. Results are merged into a local JSON store. Deadline changes between syncs are flagged as extensions.
4. Notifications use Windows toasts and the built-in speech synthesizer.

## Project layout

```
app.py          GUI, tray and command-line entry point
jobs.py         background jobs (--check, --remind, ...)
lms_scraper.py  portal sign-in and scraping
deadlines.py    deadline parsing and urgency classification
tracker.py      local store + change detection
notifier.py     toast and voice alerts
automation.py   scheduled tasks, shortcuts, start with Windows
tray.py         system tray icon
secure_store.py DPAPI password encryption
config.py       paths, settings, logging
build.py        PyInstaller + Inno Setup build
installer.iss   installer definition
```

## Troubleshooting

- **"Sign-in failed"** – check enrollment, password and campus in Settings. The portal's own error text is shown.
- **Nothing happens at 7 PM** – the PC must be on and you signed in. Settings → Background automation should say "Enabled".
- **Details** – Activity tab, or the log file in the data folder.

## License

MIT © Nobody243
