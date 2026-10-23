# Changelog

## 1.5.5 - 2026-10-23

- On a PC without Google Chrome, the first check no longer fails with "Sign-in failed: This LinkedIn profile is already associated with another student." The sign-in had in fact succeeded; the downloaded browser engine was a moment slower to leave the login page, and the app judged too early, quoting a hidden notice from that page. It now waits for the portal's redirect, reads only visible messages, and prefers the full Chromium engine over the headless shell. Found by a new clean-machine install test that runs the release on a fresh Windows with Chrome hidden.
- The sign-in window fits small screens: the card, its text and the theme switch follow the window, and the gaps tighten on short windows (a 1366x768 laptop at 125 % scaling). The main window also leaves less of the screen unused on such laptops.
- The enrollment number no longer appears in the log (the sign-in line shows its last three characters), since logs get pasted into issues.

## 1.5.4 - 2026-10-23

- Between semesters: when the portal lists no courses yet, every page says so instead of showing last semester's data, alerts pause after one notice, and everything fills in on the first check after registration. Announcements from an earlier semester are cleared once the new one has data.
- Failed background checks are counted, not announced one by one: a portal outage is reported after three failures in a row (and every third after that), a rejected sign-in once. The Dashboard's "Last sync" line shows how many checks have failed since the last good one.
- A "Something went wrong" dialog for errors inside the window, with Copy details, Open log and a pre-filled GitHub issue (app version, Windows version and the error lines; nothing else). Until now such errors were invisible in the packaged app.

## 1.5.3 - 2026-10-23

- Uninstalling with cloud checks on now offers to turn them off, so your portal login does not stay in a GitHub workflow that keeps running after the app is gone. Silent uninstalls leave the cloud alone. The same is available from the command line as `--disable-cloud`.

## 1.5.2 - 2026-10-23

- Pillow updated to 13.0.0, which closes eight published vulnerabilities in the image library (CVE-2026-96636 to 96644 and GHSA-78g4-xqwv-q3g8); the dependency audit is clean again.
- Third-party licence notes list PyNaCl and libsodium, used since 1.5.0 to seal the cloud-check secrets.
- Website: robots.txt and sitemap.xml, canonical and per-page social tags, structured data for the app, a current social card, a 180 px touch icon, and the GitHub repository's description and topics.

## 1.5.1 - 2026-10-23

- When the last three cloud checks have failed, the PC shows one desktop notification pointing at Settings > Cloud checks and the Actions page (checked when the app opens and after the PC's own daily check; one notification per streak).
- The cloud workflow commits a timestamp on every run, because GitHub switches off the schedule of a repository that has had no commits for 60 days, which a quiet semester break would have triggered. Existing cloud setups receive the new workflow automatically.
- Website: a Cloud checks walkthrough page with screenshots of every step.

## 1.5.0 - 2026-10-23

- Cloud checks: alerts with the PC off. Settings → Cloud checks sets up, after a consent screen and a one-time GitHub code, a private repository in your own GitHub account whose workflow runs the same check at 8 AM and 7 PM on GitHub's machines and sends the phone and email alerts. Your login and channel keys go there as GitHub Actions secrets, sealed on the PC with the repository's key; the PC's cache is copied so the cloud knows what is new; settings changed on the PC follow automatically; an app update moves the workflow to the new version; the PC keeps desktop and voice alerts and leaves phone and email to the cloud so nothing arrives twice. Turn off removes the secrets and the workflow. No server of ours is involved. Run now and the last result are shown in Settings.
- Settings can be given as `AM_<KEY>` environment variables (how the cloud runner receives them).

## 1.4.6 - 2026-10-23

- The background checks now suit a laptop. The 7 PM check wakes a sleeping or hibernating PC, runs on battery (before, Windows skipped it whenever the charger was out and killed it if you unplugged mid-check), runs as soon as the PC is back if 7 PM was missed, and retries up to three times, ten minutes apart, if the portal was unreachable. The hourly reminder and the sign-in catch-up also run on battery; the hourly one never wakes the PC. Tasks created by an earlier version are re-registered with these settings the first time the app opens. A PC that is shut down still checks nothing; see the website's FAQ.
- Reading a page no longer fails with "page is navigating and changing the content" when a course change is still loading on a slow connection; the read waits and retries.

## 1.4.5 - 2026-10-23

- Phone pushes work. Every push, including the test after pairing, failed with "could not deserialize key data": the signing key the PC generates is stored as PEM text, and the push library only accepts a key given as text when it is a file path or a bare base64 key. The key is now loaded and handed over as an object. Nothing to redo: the pairing and the stored keys were fine.

## 1.4.4 - 2026-10-23

- The Pair a phone dialog explains itself: three numbered steps (open the Camera app, point it at the code, tap Allow on the page), a status line that changes to "your phone opened the page, now tap Allow" the moment the link is opened, and two ways round a camera that will not scan: Copy link, or Email me the link when email is set up. The link stays valid for ten minutes.
- Pairing on a mobile network no longer fails with "the relay answered 429": the relay rate-limits by public address and carrier networks put thousands of phones behind one. The phone page now waits the relay's suggested time and retries, then moves on to three other public relays, and the PC watches all of them.

## 1.4.3 - 2026-10-23

- Pages cross-fade into each other. Tk cannot fade hundreds of widgets, so the app photographs the page it is leaving and the one it is opening and blends the two pictures over the page area; one image moving is smooth where moving every widget never was. Off with the Animations switch.
- Long lists are built in parts: the Lectures, Assignments, Attendance and Announcements pages create the first screenfuls of rows at once and the rest as you scroll towards them, so a heavy page opens in a fraction of the time and repaints faster while it scrolls. Ctrl+End builds the rest first.
- Lighter rows: the week, assignment, class and announcement rows are one frame with a grid inside instead of frames nested three deep, and separators are plain lines rather than drawn canvases; a page of ninety weeks has a few hundred fewer widgets.
- Pages open in about half the time: CustomTkinter's scrollbar redrew itself and forced every pending layout to finish for each widget added to a list; it is now updated once per idle cycle.

## 1.4.2 - 2026-10-22

- Faster, calmer window: pages are rebuilt only when the data or settings behind them changed (the dashboard also once a minute for its countdowns), and they are built before they are shown, so switching between pages is instant and a page no longer assembles itself on screen; the page slide-in is gone because it re-laid out every widget for a dozen frames; the remaining animations run at 30 frames a second.
- Smoother scrolling: wheel events are gathered and applied once per frame instead of repainting the page for every one of the burst a precision wheel or touchpad sends, each step waits for its repaint before the next lands (the striped, half-drawn text while scrolling fast came from steps landing on a page that was still painting), and a notch moves 40 px instead of 20.
- The wheel scrolls a page anywhere on it, including over the toolbar above the list on Assignments, Attendance, Timetable, Announcements and Lectures. PageUp / PageDown scroll by a screen, Ctrl+Home / Ctrl+End jump to the ends.
- Website: screenshots retaken from this build and the dashboard tour re-aimed at the cards, which had moved down when today's classes joined the page.

## 1.4.1 - 2026-10-22

- Fix: the Dashboard, Exams and Settings pages could not be scrolled and their content was pinned to the window height (since 1.3.1, when the page slide-in started reconfiguring the wrong frame). Settings is reachable to the bottom again.
- Fix: the Timetable page's own scroll region was being replaced by its resize handler.
- Smoother fast scrolling: hover highlights pause while the wheel is turning, so rows sliding under the pointer no longer trigger a redraw storm that tore the text.

## 1.4.0 - 2026-10-22

- Alerts on your phone and in your inbox. Settings → Phone, email and calendar: link your own mailbox (Gmail, Outlook, the university's Microsoft 365 or any SMTP server) with an app password, and pair a phone by scanning a QR code; no app to install, no account, and nothing passes through a server of ours. Every alert the app already raises on Windows is delivered to the linked channels too.
- Calendar: an .ics file of deadlines and exams in Documents › Assignment Monitor, rewritten after every sync, and optional emailed calendar invites that appear in Google Calendar or Outlook on the phone. Both off until you turn them on.
- Timetable: the CMS week drawn as a clean grid, in the app and saved as PNG, JPG or PDF. Today's classes on the dashboard with the one happening now highlighted.
- Miscellaneous files: the LMS Miscellaneous page of every course (project briefs, templates, past papers) under a toggle on the Lectures page, downloadable like lecture notes into course / Miscellaneous folders.
- Attendance: the first read of a new file kind never fires alerts for files that were already there.

## 1.3.3 - 2026-10-22

- Attendance page rebuilt as one list of every registered course, weakest first, with filters for courses under the minimum, at risk and on track. Click a course for its classes, or switch the page to every class or only the missed ones.

## 1.3.2 - 2026-10-22

- New colour scheme in both themes: cool slate greys with a single indigo accent, calmer state colours, and a sidebar and status bar a shade off the page so the shell frames the content. Pills are fully rounded and nav items a little softer.

## 1.3.1 - 2026-10-22

- Design pass: rounded surfaces that lift on hover, a short slide when switching pages, a fade when switching themes, counters that count up and attendance bars that fill in. All of it can be switched off with the new Animations switch in Settings, Appearance.
- Faster: fonts are built once and reused instead of being created for every label, so pages open quicker and use less memory.
- Sign-in screen copy covers everything the app watches.

## 1.3.0 - 2026-10-22

- Lectures: every course's lecture notes in one list, by week, with a checkbox per file. Tick what you want and "Download selected" fetches the files through the app's own sign-in into a folder you choose (Documents / Assignment Monitor / Lectures by default), organised as course / week - title. Files already on disk are skipped; video links open in the browser.
- A notification when new lecture notes are uploaded (switchable, like the other trackers).
- Attendance, exam and announcement alerts are Windows notifications only; the voice is kept for assignment reminders.

## 1.2.0 - 2026-10-21

- Attendance: every course's present, absent and total hours with the percentage, how many hours you can still miss (or need to attend) for the minimum you set, and the class-by-class record with topics. An alert when a new absence is recorded or a course drops under the minimum.
- Exams: the seating plan with date, session, time, room, row and seat for every paper, a countdown on the dashboard, a reminder the day before (configurable) and once on the morning of the paper, and an alert when the plan is posted or a room changes.
- Announcements: every course's LMS announcements in one place, newest first, with an alert for each new one.
- Three new pages (Attendance, Exams, Announcements), dashboard cards for attendance and the next exam, and a Campus tracking section in Settings to switch each one on or off and set the attendance minimum.
- One signed-in session now reads everything; a page that cannot be read is skipped and logged instead of failing the sync.
- `--status` prints attendance and upcoming exams as well as assignments.

## Unreleased

- Typography: the app now ships the Inter typeface (regular, medium, semibold and a display cut for headings) with Segoe UI as the fallback, on a golden-ratio type scale. Nothing is set in bold any more; headings are semibold.
- Colour: the accent and every status colour (due today, soon, this week, submitted, extended) sit one golden angle apart on the colour wheel, in both themes, and all pass AA contrast.
- Website: same Inter typography and golden-ratio heading scale, no italics; the Download button in the nav opens a chooser (installer, portable zip, guide); phones, Macs and Linux get "Send to your PC" instead of a 60 MB installer they cannot run; the changelog page is gone (release notes live on GitHub).

## 1.1.0 - 2026-10-20

- New app icon (dial with a deadline ping) across the app, installer, tray and website.
- Voice settings: choose the Windows voice, volume and speaking rate for spoken reminders, with a test button.
- Uninstalling now removes everything: running copies are closed, the scheduled tasks and Startup entry are unregistered, and you are asked whether to delete the saved sign-in and cached data.
- Installer and workflow are ready for SignPath code signing (used automatically once the project is approved).
- Website: https://assignment-monitor.vercel.app

## 1.0.0 - 2026-10-19

- First release: dashboard, assignments, settings and activity pages; light and dark themes; tray mode.
- Background checks through Windows Task Scheduler (daily, hourly reminders, at sign-in).
- Spoken and toast reminders on due days; extended-deadline detection.
- In-app updater that checks numbered GitHub releases.
- Per-user installer (no administrator rights) and a portable zip.
