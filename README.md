# Assignment Monitor

**for Bahria University LMS** · unofficial, open source, Windows · [website](https://assignment-monitor.vercel.app)

A desktop app that keeps an eye on your LMS assignments so you don't have to. Install it, sign in once, and it quietly does the rest.

- Dashboard: next deadline, what's pending, due today, due this week, extended, overdue, submitted
- Catches **extended deadlines**, which the portal hides by merging the old and new dates into one string
- **Checks automatically** every day at 7 PM and when you sign in to Windows
- **Reminds you aloud every hour** on the day an unsubmitted assignment is due
- Lives in the **system tray**, can start with Windows, light and dark themes, keyboard shortcuts

## Install

1. Download **`AssignmentMonitor-Setup.exe`** from the [latest release](https://github.com/Nobody243/Assignment_Monitor/releases/latest).
2. Run it. It installs for your user account only (no administrator password) and adds a Start Menu and Desktop icon.
3. Open Assignment Monitor, enter your enrollment number, CMS password and campus, leave "Check automatically" ticked, and click **Connect and start monitoring**.

That's it. The app verifies the sign-in, reads your assignments and registers the background checks.

Prefer no installer? `AssignmentMonitor-portable.zip` from the same release runs from any folder.

> Windows SmartScreen may warn the first time because the app isn't code-signed. Click **More info**, then **Run anyway**. You can always build it yourself from source (below).

**Requirements:** Windows 10 or 11. Google Chrome is used if installed; otherwise a browser engine is downloaded once automatically.

## Using it

| Screen | What it does |
| --- | --- |
| **Dashboard** | Next deadline, counters, needs-attention list sorted by deadline, per-course progress. Click a counter or course to filter. |
| **Assignments** | Full list with filters, course picker and search. Shows extension history and marks. |
| **Settings** | Account and campus, theme, tray and start-with-Windows options, notifications (voice, volume, speed, days ahead), automatic checks, data folder, privacy and licenses. |
| **Activity** | Log of every sync and reminder, including the scheduled background runs. |

Shortcuts: **F5** sync · **Ctrl+1…4** switch pages · **Ctrl+F** search · **Esc** clear search.

**Tray:** closing the window keeps the app in the system tray (switchable in Settings). Right-click the tray icon to open, sync now, or quit. "Start with Windows" opens it minimized to the tray at sign-in. Launching the app while it is already running just brings the window back.

**Automatic checks** are three Windows scheduled tasks for your user account:

| Task | When | What |
| --- | --- | --- |
| `AssignmentMonitor_DailyCheck` | Daily 19:00 | Sync + notifications |
| `AssignmentMonitor_LogonCheck` | 2 min after sign-in | Catch-up sync if the PC was off at 19:00 |
| `AssignmentMonitor_HourlyReminder` | Every hour | Voice + toast while something unsubmitted is due today |

They run even when the app is closed. Turn them off any time from Settings; uninstalling removes them too.

**Updating:** the app checks GitHub for a newer numbered release when it starts and shows "Update available · Install" at the top. One click downloads the installer and reinstalls over the current version; your sign-in and data are kept. You can turn the check off in Settings.

## Privacy and security

- Your password is encrypted with Windows Data Protection (DPAPI) for your user account and stored in `%LOCALAPPDATA%\Assignment Monitor\settings.env`. It is only ever sent to `cms.bahria.edu.pk` when signing in.
- Assignment data, logs and the browser profile stay in that same local folder. There is no server, no account, no telemetry.
- The app only reads your own assignments page; it never submits or changes anything on the portal.

Details: [PRIVACY.md](PRIVACY.md) · [SECURITY.md](SECURITY.md) · [THIRD_PARTY_LICENSES.md](THIRD_PARTY_LICENSES.md)

**Code signing policy:** free code signing for releases is provided by [SignPath.io](https://signpath.io), certificate by [SignPath Foundation](https://signpath.org). Numbered releases are signed automatically by the CI pipeline once the project is approved; see [CODE_SIGNING_POLICY.md](CODE_SIGNING_POLICY.md).

Assignment Monitor is an independent student project and is not affiliated with, endorsed by, or supported by Bahria University.

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
python app.py --quit                 ask the running instance to quit
python app.py --setup                open the sign-in screen (switch account)
python app.py --enable-automation    register the background tasks
python app.py --disable-automation   remove them
```

When running from source, data lives in the project folder (`.env`, `data/`, `chrome_profile/`), all git-ignored.

## Tests and build

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
pytest                # unit tests: deadline parsing, change tracking, settings encryption, scraper parsing
python build.py       # dist/AssignmentMonitor-portable.zip and, with Inno Setup 6, dist/AssignmentMonitor-Setup.exe
```

GitHub Actions runs lint, tests and a dependency audit on every push. Every commit on `main` also builds the installer and zip and refreshes the rolling **Latest build** pre-release; pushing a tag like `v1.0.0` publishes a numbered release. The app checks numbered releases when it starts (switchable in Settings) and can download and install the update itself.

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
tests/          pytest suite
```

## Troubleshooting

- **"Sign-in failed"** – check enrollment, password and campus in Settings. The portal's own error text is shown.
- **Nothing happens at 7 PM** – the PC must be on and you signed in. Settings → Automatic checks should say "Enabled".
- **Details** – Activity tab, or the log file in the data folder.

## License

MIT © Nobody243
