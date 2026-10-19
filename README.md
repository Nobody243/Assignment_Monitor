# Bahria LMS Monitor

A Windows desktop app for Bahria University students that keeps an eye on your LMS assignments so you don't have to.

It signs in to the CMS/LMS portal for you, reads every course's assignments, and then:

- shows a clean dashboard of what's pending, due today, due this week, extended, overdue and submitted
- notices when a teacher **extends a deadline**, even though the portal squashes the old and new dates together
- runs a **daily check at 7 PM** and a catch-up check when you sign in to Windows
- **reminds you aloud every hour** on the day an unsubmitted assignment is due
- comes in **dark and light** themes

No Python, no setup scripts. Download, run, sign in once.

## Download

Grab `BahriaLMSMonitor-windows.zip` from the [latest release](https://github.com/Nobody243/Bahria-LMS-Monitor/releases/latest), extract it anywhere, and run `BahriaLMSMonitor.exe`.

On first launch enter your enrollment number, CMS password and campus. The app verifies the sign-in, reads your assignments and, if you leave the box ticked, sets up the background automation. That's it.

> Windows SmartScreen may warn about an unsigned app the first time. Click "More info" then "Run anyway".

**Requirements:** Windows 10/11. Google Chrome is used if installed; otherwise a browser engine is downloaded once automatically.

## What's inside

| Screen | What it does |
| --- | --- |
| **Dashboard** | "Up next" card, counters for pending / due today / due this week / extended / overdue / submitted, a needs-attention list sorted by deadline, per-course progress. Click any counter or course to filter. |
| **Assignments** | Full list with filters, course picker and search. Shows extension history and marks. |
| **Settings** | Account and campus, dark/light theme, voice and notification preferences, background automation on/off, data folder, switch account. |
| **Activity** | Log of every sync and reminder, including the scheduled background runs. |

### Background automation

Turning it on registers three Windows scheduled tasks for your user account (no admin rights needed):

| Task | When | What |
| --- | --- | --- |
| `BahriaLMS_DailyCheck` | Daily 19:00 | Sync + notifications |
| `BahriaLMS_LogonCheck` | 2 min after sign-in | Catch-up sync if the PC was off at 19:00 |
| `BahriaLMS_HourlyReminder` | Every hour | Voice + toast while something unsubmitted is due today |

It also adds Desktop and Start Menu shortcuts. Turn it off any time from Settings.

## Privacy

- Your password is encrypted with Windows Data Protection (DPAPI) for your user account and stored in `%LOCALAPPDATA%\Bahria LMS Monitor\settings.env`. It is only ever sent to `cms.bahria.edu.pk` when signing in.
- Assignment data, logs and the browser profile stay in that same local folder. Nothing is sent anywhere else.

## Run from source

```bash
git clone https://github.com/Nobody243/Bahria-LMS-Monitor.git
cd Bahria-LMS-Monitor
pip install -r requirements.txt
python app.py
```

Command-line modes (also what the scheduled tasks call):

```
python app.py --check         sync and notify
python app.py --check -q      sync without notifications
python app.py --remind        hourly same-day reminder
python app.py --status        print saved assignments
python app.py --test-alert    test notification and voice
python app.py --setup         open the sign-in screen (switch account)
```

When running from source, data lives in the project folder (`.env`, `data/`, `chrome_profile/`), all git-ignored.

## Build the executable

```bash
pip install -r requirements.txt pyinstaller
python build.py
```

Produces `dist/BahriaLMSMonitor/` and `dist/BahriaLMSMonitor-windows.zip`. Pushing a tag like `v2.1.0` runs the same build on GitHub Actions and attaches the zip to a release.

## How it works

1. Playwright drives Chrome headlessly: sign in at `cms.bahria.edu.pk`, follow the CMS → LMS single sign-on, open `Student/Assignments.php`.
2. For every course in the semester dropdown it reads the assignments table. The portal concatenates an extended deadline with the original (`4 October 2026 - 11:50 am13 September 2026-11:55 am`); the parser splits those apart.
3. Results are merged into a local JSON store. Deadline changes between syncs are flagged as extensions.
4. Notifications use Windows toasts (`winotify`) and the built-in speech synthesizer.

## Project layout

```
app.py          GUI + command-line entry point
jobs.py         background jobs (--check, --remind, ...)
lms_scraper.py  portal sign-in and scraping
deadlines.py    deadline parsing and urgency classification
tracker.py      local store + change detection
notifier.py     toast and voice alerts
automation.py   scheduled tasks and shortcuts
secure_store.py DPAPI password encryption
config.py       paths, settings, logging
build.py        PyInstaller build
```

## Troubleshooting

- **"Sign-in failed"** – check enrollment, password and campus in Settings. The portal's own error text is shown.
- **Nothing happens at 7 PM** – the PC must be on and you signed in. Settings → Background automation should say "Enabled".
- **Details** – Activity tab, or the log file in the data folder.

## License

MIT © Nobody243
