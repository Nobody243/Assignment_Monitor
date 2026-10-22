# Changelog

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
