# Assignment Monitor

**for Bahria University LMS** · unofficial, open source, Windows · [website](https://assignment-monitor.vercel.app)

A desktop app that keeps an eye on your LMS and CMS so you don't have to: assignments, attendance, exams, announcements, lecture notes and your timetable. Install it, sign in once, and it quietly does the rest, on your PC, on your phone and in your inbox if you want.

- Dashboard: next deadline, what's pending, due today, due this week, extended, overdue, submitted
- Catches **extended deadlines**, which the portal hides by merging the old and new dates into one string
- **Checks automatically** every day at 7 PM and when you sign in to Windows
- **Reminds you aloud every hour** on the day an unsubmitted assignment is due
- **Attendance** per course with the margin to your minimum, class-by-class, and an alert when an absence is recorded
- **Exam seating plan** with room and seat, a countdown, a reminder the day before and on the morning of each paper
- **Announcements** from every course in one place, with an alert for each new one
- **Lecture notes** and **Miscellaneous files** from every course in one list; tick the files you want and download them into tidy folders
- **Timetable** from the CMS drawn as a clean week grid, saved as PNG, JPG or PDF; today's classes on the dashboard
- **Phone and email alerts** through your own mailbox and your phone's browser, and an optional **calendar** of deadlines and exams
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
| **Dashboard** | Next deadline, counters, today's classes with the one happening now highlighted, attendance margins, next exam, latest announcements. Click a counter or card to open the page behind it. |
| **Assignments** | Full list with filters, course picker and search. Shows extension history and marks. |
| **Attendance** | Every registered course in one list, weakest first, with filters for courses under the minimum, at risk and on track. Click a course for its classes, or switch the page to every class or only the missed ones. |
| **Exams** | The seating plan: date, session, time, room, row and seat for each paper, with a countdown; papers not yet scheduled are listed too. |
| **Announcements** | Every course's LMS announcements, newest first, filterable by course. |
| **Timetable** | The week as a grid, one row per day, colour per course, with room and teacher. Save as PNG, JPG or PDF. |
| **Lectures** | Every course's lecture notes by week, and under a toggle the Miscellaneous files, with a checkbox per file. Download the selection into a folder you choose, organised as course / week - title (or course / Miscellaneous - type); existing files are skipped. |
| **Settings** | Account and campus, theme, tray and start-with-Windows options, notifications (voice, volume, speed, days ahead), phone, email and calendar, campus tracking (attendance minimum, exam reminder lead, what to read), automatic checks, data folder, privacy and licenses. |
| **Activity** | Log of every sync and reminder, including the scheduled background runs. |

Shortcuts: **F5** sync · **Ctrl+1…9** switch pages · **Ctrl+F** search · **Esc** clear search.

### Phone, email and calendar

All three live in Settings → Phone, email and calendar and are off until you turn them on. Every alert the app raises on Windows is also delivered to whatever you link.

- **Phone.** Press **Pair a phone** and scan the QR code with the phone's camera. A page on the website opens; tap **Allow notifications** and a test alert arrives. Nothing to install and no account: the pushes go from your PC to the phone's browser push service, encrypted end to end. Android works with Chrome or Samsung Internet; iPhone needs iOS 16.4 or newer and the page added to the Home Screen first (the page says so). Unpair any time.
- **Email.** Enter your address and an *app password* (Gmail: 2-Step Verification → App passwords; Outlook and the university's Microsoft 365: Security → App passwords). The server is picked from the address; **Advanced** sets it by hand. Mail goes from your mailbox to itself; nobody else handles it.
- **Calendar.** One switch keeps `Documents\Assignment Monitor\Assignment Monitor.ics` up to date with deadlines and exams after every sync (import it once into Google Calendar or Outlook). A second switch emails a calendar invite for each new deadline and exam, which Google Calendar and Outlook add to the phone's calendar on their own.

### Timetable

The CMS timetable is read with every sync and drawn the app's way: one row per day, a colour per course, room and teacher on each block, back-to-back slots merged into one class. **Save as PNG / JPG / PDF** writes the same picture for a lock screen or a print.

**Tray:** closing the window keeps the app in the system tray (switchable in Settings). Right-click the tray icon to open, sync now, or quit. "Start with Windows" opens it minimized to the tray at sign-in. Launching the app while it is already running just brings the window back.

**Automatic checks** are three Windows scheduled tasks for your user account:

| Task | When | What |
| --- | --- | --- |
| `AssignmentMonitor_DailyCheck` | Daily 19:00 | Sync (assignments, attendance, exams, announcements, lecture notes and files, timetable) + notifications, including "exam tomorrow", plus the calendar file and invites when enabled |
| `AssignmentMonitor_LogonCheck` | 2 min after sign-in | Catch-up sync if the PC was off at 19:00 |
| `AssignmentMonitor_HourlyReminder` | Every hour | Voice + toast while something unsubmitted is due today, plus one reminder on the morning of an exam |

They run even when the app is closed. Turn them off any time from Settings; uninstalling removes them too.

**Updating:** the app checks GitHub for a newer numbered release when it starts and shows "Update available · Install" at the top. One click downloads the installer and reinstalls over the current version; your sign-in and data are kept. You can turn the check off in Settings.

## Privacy and security

- Your password is encrypted with Windows Data Protection (DPAPI) for your user account and stored in `%LOCALAPPDATA%\Assignment Monitor\settings.env`. It is only ever sent to `cms.bahria.edu.pk` when signing in. The email app password and the phone's push keys are stored the same way.
- Assignments, attendance, the exam plan, announcements, the lecture and file lists, the timetable, logs and the browser profile stay in that same local folder. There is no server, no account, no telemetry.
- The app only reads your own pages (LMS assignments, announcements, lecture notes and Miscellaneous files; CMS attendance, exam seating and timetable); it never submits or changes anything on the portal. Each of these can be switched off in Settings. Files are downloaded only when you click Download, to a folder you choose.
- Phone and email alerts, when enabled, go from your PC to your own mail server and to your phone's browser push service. The website only passes the phone's push address to your PC once, encrypted, during pairing; it keeps no accounts and no data.

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
python app.py --view timetable       open the window on a given page
python app.py --enable-automation    register the background tasks
python app.py --disable-automation   remove them
```

When running from source, data lives in the project folder (`.env`, `data/`, `chrome_profile/`), all git-ignored.

## Tests and build

```bash
pip install -r requirements-dev.txt
ruff check .          # lint
pytest                # unit tests: deadline parsing, change tracking, settings encryption, portal parsing, timetable rendering, calendar, channels
python build.py       # dist/AssignmentMonitor-portable.zip and, with Inno Setup 6, dist/AssignmentMonitor-Setup.exe
```

GitHub Actions runs lint, tests and a dependency audit on every push. Every commit on `main` also builds the installer and zip and refreshes the rolling **Latest build** pre-release; pushing a tag like `v1.0.0` publishes a numbered release. The app checks numbered releases when it starts (switchable in Settings) and can download and install the update itself.

## How it works

1. Playwright drives Chrome headlessly: one sign-in at `cms.bahria.edu.pk`, the CMS pages (attendance, attendance detail, exam seating, timetable), then the CMS → LMS single sign-on and, for every course in the semester dropdown, the assignments, announcements, lecture-notes and Miscellaneous pages. Each reader fails on its own; the others still return.
2. The portal concatenates an extended deadline with the original (`4 October 2026 - 11:50 am13 September 2026-11:55 am`); the parser splits those apart. Timetable blocks carry the full course, teacher, class, room and time range in a title attribute; back-to-back slots are merged.
3. Results are merged into local JSON stores. Deadline changes are flagged as extensions, new absences and courses dropping under the minimum are detected, new announcements and files are listed, and the first read of anything new is silent.
4. Alerts go out as Windows toasts, the built-in voice for assignments, and, when linked, email from your own mailbox and Web Push to your phone. The calendar file and invites are refreshed after the sync.

## Project layout

```
app.py               GUI, tray and command-line entry point
jobs.py              background jobs (--check, --remind, ...) and the shared sync processing
lms_scraper.py       portal sign-in, the readers for every page, lecture and file downloads
campus.py            parsers for attendance, exam seating, announcements, lecture notes, Miscellaneous files, timetable
deadlines.py         deadline parsing and urgency classification
tracker.py           local stores + change detection
notifier.py          toast and voice alerts, fan-out to the linked channels
channels.py          email (your own SMTP) and Web Push to a paired phone, QR pairing
calendar_export.py   the .ics file and emailed calendar invites
timetable_render.py  the week grid as PNG, JPG or PDF
updater.py           in-app updates from GitHub releases
automation.py        scheduled tasks, shortcuts, start with Windows
tray.py              system tray icon
secure_store.py      DPAPI encryption for the password and channel secrets
config.py            paths, settings, logging
build.py             PyInstaller + Inno Setup build
installer.iss        installer definition
tests/               pytest suite
website/             the site (React + Vite; three.js planet, GSAP, Lenis, Framer Motion), the /phone pairing page and its service worker, deployed to Vercel from this folder
```

The website lives in `website/`: `npm install`, `npm run dev` for a dev server, `npm run build` for the static bundle in `website/dist`. Vercel builds it from the `website` root directory on every push to `main`.

## Troubleshooting

- **"Sign-in failed"** – check enrollment, password and campus in Settings. The portal's own error text is shown.
- **Nothing happens at 7 PM** – the PC must be on and you signed in. Settings → Automatic checks should say "Enabled".
- **Details** – Activity tab, or the log file in the data folder.
- **Email test fails** – use an app password, not your normal one (Gmail: 2-Step Verification → App passwords; Outlook: Security → App passwords). Corporate or university mailboxes sometimes block SMTP; the Advanced button lets you set the server.
- **Phone pushes stop** – the phone's browser rotated its push address or you cleared the site's data. Press Pair a phone again; it takes ten seconds.

## License

MIT © Nobody243
