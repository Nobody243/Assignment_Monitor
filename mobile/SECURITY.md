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
| Portal password | **Not kept** | With the desktop app, never on the phone. With the phone-only setup it is typed once, sealed on the phone and sent to GitHub, then forgotten (see "Phone-only setup" below). The phone never contacts the portal. |

Network: HTTPS only (`usesCleartextTraffic=false`, a network-security config with cleartext refused), and only to
`github.com` (device-flow sign-in) and `api.github.com` (read `state/summary.json` from the student's own private
repository; the phone-only setup also creates and manages that repository, see below). That also holds in the background: about every two hours Android runs a short check (WorkManager) that
reads the same file with the same sign-in to look for news; it needs no extra permission beyond the network. No analytics,
no crash reporting, no third party. The link opened during sign-in is checked to be
`https://github.com` before it is launched.

Exports: the calendar file and the timetable picture are made on the phone and handed to Android's share sheet; the
app does not send them anywhere itself. "Copy support info" puts versions, freshness and counts on the clipboard, with no
name, course, grade or token (a test asserts it).

## Phone-only setup (Cloud checks from the phone)

Sign-in screen, "I only use the phone", and Settings, Cloud checks. It does what the desktop's Cloud checks setup does
(`cloud.py`), from the phone, so a student without the desktop app gets the same private repository
(`assignment-monitor-cloud`), the same scheduled workflow and the same `state/summary.json`. What changes about the
claims above, stated exactly:

- **The portal password is typed on the phone once.** It is sealed on the phone with the repository's public key (a
  libsodium sealed box, `pinenacl`; the format is checked against a box sealed by libsodium itself, in both directions)
  and sent over HTTPS to GitHub's Actions secrets of the student's own private repository (`AM_PASSWORD`, with
  `AM_ENROLLMENT`). It goes to GitHub and nowhere else: not to us, and the phone never contacts the portal.
- **It is not kept on the phone.** Not in preferences, not in secure storage, not in a log line, not in an error message
  (errors carry the step and the HTTP status only, never a request body, a response body or an exception's text). The
  field is cleared when the setup succeeds and when the screen is left. While a setup that failed is still on screen the
  password stays in that text field's memory so Retry works; it is never written anywhere. Tests assert that no request
  body, stored value, error text or debug line holds it.
- **The GitHub sign-in is wider for this path.** It asks for `repo workflow` (creating the repository and writing the
  workflow file need both), kept in the Android Keystore like the read-only token. A student who wants the narrow
  read-only sign-in can still switch to "Use a read-only token instead" once Cloud checks is set up.
- **Where the check runs.** On GitHub's machines, twice a day, from the student's own repository, with the secrets
  GitHub keeps encrypted; GitHub masks them in logs. The workflow checks out the project at a pinned release tag
  (`cloudRunnerVersion` in `lib/cloud_setup.dart`), and the setup refuses to start if that release is not published.
- **Turning off** (Settings, Cloud checks) deletes every secret and the workflow file. The repository stays; deleting it
  needs a permission the app does not ask for.

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
  - **phone-only setup**: the sealed box, the workflow file (identical to the desktop's), the whole sequence against a
    fake GitHub (exact calls, secret names, sealed not plain, running twice, public repository, 401, 403, 422, rate limit),
    that the password never appears in a request, store, error or log, and the wizard and Settings screens;
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
