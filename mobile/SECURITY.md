# Phone app: security and quality notes

What the app holds, what it sends, what is checked, and what is still open. Updated with each change that touches them.

## What the phone holds and sends

| Item | Where | Notes |
| --- | --- | --- |
| GitHub sign-in token | Android Keystore through `flutter_secure_storage` | Never logged, never shown, deleted on sign out. |
| Last `summary.json` (name, courses, grades, timetable, seat numbers) | Android Keystore (encrypted, same vault as the token) | A copy left in plain preferences by an older build is moved into the vault and removed on first read. Backups and device-to-device copies are switched **off** (`allowBackup=false`, data-extraction rules). Deleted on sign out. |
| Screen content | `FLAG_SECURE` (Settings, Security, Screen privacy; on by default) | Screenshots and screen recordings are black and the recent-apps preview is blank. |
| Notification text | Generic while the app lock is on | Reminders say only "Assignment due soon", news and summaries are generic too; details are inside the locked app. |
| First-run setup | One time, after the first real data | Reminder lead times and notification permission, then an offer to turn the app lock on. |
| Settings (palette, lead times, done and snoozed assignments) | `shared_preferences` | No personal data beyond assignment ids. |
| Portal password | **Never** on the phone | The phone never contacts the portal. |

Network: HTTPS only (`usesCleartextTraffic=false`, a network-security config with cleartext refused), and only to
`github.com` (device-flow sign-in) and `api.github.com` (read `state/summary.json` from the student's own private
repository). That also holds in the background: about every two hours Android runs a short check (WorkManager) that
reads the same file with the same sign-in to look for news; it needs no extra permission beyond the network. No analytics,
no crash reporting, no third party. The link opened during sign-in is checked to be
`https://github.com` before it is launched.

Exports: the calendar file and the timetable picture are made on the phone and handed to Android's share sheet; the
app does not send them anywhere itself. "Copy support info" puts versions, freshness and counts on the clipboard, with no
name, course, grade or token (a test asserts it).

## Checks that run (CI: `.github/workflows/mobile-ci.yml`, and locally)

- `flutter analyze`: no issues allowed.
- `flutter test --coverage` (about 80 tests, floor 70 percent, `python tools/dart_coverage.py --min 70`):
  - **contract**: empty, sparse and damaged `summary.json` files (built by the real `summary.build`, see
    `tools/make_mobile_fixtures.py`) must read and draw on every screen; a Python test keeps the fixtures in step with
    the builder;
  - **layout**: every screen on a 360 x 740 phone at 100, 150 and 200 percent text, light and dark, with a real font,
    must not overflow; the side menu must scroll rather than hide Sign out;
  - **contrast**: text, secondary text, accent and status colours at least 4.5 to 1 in all four palettes, light and dark;
  - **alerts**: the Sunday summary, morning digest, what-changed comparison, calendar file (escaping, folding, times) and
    the background check (new, unchanged, alerts off, first run, signed out, offline);
  - **behaviour**: sign-in (device flow, declined, expired), refresh (304, offline, 401, no double refresh), sign out,
    reminder planning, swipe to done and snooze, calculator, announcements, settings, the intro, and fast taps on the
    menu and bar.
- `python tools/dart_osv_check.py`: every locked package against osv.dev; fails on a known vulnerability.
- Python side (same CI as the desktop app): ruff, bandit, gitleaks, pytest including the summary hardening tests.

## Known gaps (not hidden)

1. **The default sign-in is broad.** GitHub's device flow cannot be limited to one repository, so "Sign in with GitHub" asks
   for `repo`. The app only reads one file. The tighter option is built: "Use a read-only token instead" takes a
   fine-grained token limited to the one repository with Contents read-only (the GitHub page opens pre-filled).
   Prefer it. The default stays the device flow because it is one tap.
2. **App lock is optional and off by default.** Settings, Security turns it on (fingerprint, face or the phone's PIN, through
   Android's own lock). It hides the app after 30 seconds away. It does not stop a screenshot of a locked screen's
   notification text: reminders show the assignment title.
3. **Test APKs are debug-signed.** The signed build is `.github/workflows/phone-release.yml` (see `RELEASE.md`): your own key
   from repository secrets, code shrinking (R8) on, a draft release. Nothing is signed or published until the four secrets
   exist and you run it, and the shrunk build must be tried on a real phone first.
4. **Announcement text** is copied from the portal as is (clipped to 600 characters) and may contain whatever a teacher
   wrote, including links or contact details. It lives only in the student's private repository and the phone.
5. **Not yet tried on a device.** Notifications (and Snooze and Done on them), the background check, the home-screen widget,
   the app lock prompt, the share sheet (timetable and calendar), the keystore and the launcher icons need a run on a real
   Android phone. iOS is a compile check in CI only (no Apple developer account, no device run; Snooze, Done and the
   background check are Android only).
