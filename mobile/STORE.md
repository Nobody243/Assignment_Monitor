# Play Store listing notes

Facts to paste into Play Console. Keep them true to `SECURITY.md`.

**App name:** Assignment Monitor
**Short description (80):** Deadlines, attendance, exams and GPA for Bahria students, with reminders. No server, no ads.
**Full description:** Assignment Monitor shows your assignments with live countdowns, how many classes you can still miss,
your exam seats, timetable, announcements and results, and reminds you before a deadline. It reads a small summary file
from your own private GitHub repository (made by the Assignment Monitor desktop app), so there is no account with us and
your portal password never reaches your phone. Free and open source.

**Category:** Education. **Contains ads:** No. **In-app purchases:** No.

## Data safety answers

| Question | Answer |
| --- | --- |
| Does the app collect or share user data? | No data is collected by the developer. The app reads the user's own file from GitHub (a third-party service chosen by the user) and keeps it on the device. |
| Data shared with third parties | None by the app. GitHub receives the user's own sign-in and read requests. |
| Is all data encrypted in transit? | Yes, HTTPS only. |
| Can users request data deletion? | Sign out in the app deletes the sign-in, the saved summary and scheduled reminders from the device. Data in the user's GitHub repository is theirs to delete there. |
| Account creation | None in the app. Sign-in is with the user's own GitHub account. |
| Permissions | Internet; notifications (reminders); biometric (optional app lock); run at start-up (restores reminders after a reboot). |

**Privacy policy URL:** https://assignment-monitor.saaddev.top/privacy (has a section for the phone app).

## Assets to prepare

Icon 512 x 512 (from `tools/make_mobile_icon.py`), a 1024 x 500 feature graphic, and 4 to 8 phone screenshots
(`mobile/screenshots/` has demo-data ones to start from).
