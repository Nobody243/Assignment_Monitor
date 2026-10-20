# Changelog

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
