# Standalone phone app: the plan

Goal: the phone app does everything the desktop app does, on its own. No desktop app and no GitHub repository are needed.
The desktop app and the cloud checker stay as other ways to use it, and the three still work together (see "Sources").

## How it works

The desktop app drives a real browser (Playwright) through the Bahria CMS and LMS. The phone does the same with a
**WebView** inside the app (the `flutter_inappwebview` plugin): it fills the sign-in form, follows the single sign-on to the
LMS, opens each page, and hands the page HTML to parsers. The parsers are ports of `campus.py`, `results.py` and
`deadlines.py` to Dart, checked against the same HTML fixtures the Python tests use, so both apps read a page the same way.

Why a WebView and not plain HTTP: the portal pages are ASP.NET with postbacks, modals and scripts. A WebView runs them as
a browser does, and it keeps the session cookie that downloads and uploads need.

## Testing

The app is run and tested in an Android emulator on the development PC (Android SDK in C:\Android\sdk, an x86_64 Google APIs image). The emulator
can open the real portal sign-in page and run the screens, but a sign-in with a real account is typed by the student.

## Security rules

- The portal password is stored only in the Android Keystore (flutter_secure_storage, already used for the token), never
  in preferences, logs or the summary cache. It is sent only to the university portal host.
- The WebView allows only the Bahria hosts (cms.bahria.edu.pk, lms.bahria.edu.pk); anything else is refused.
- Downloaded lecture and assignment files go to the app's own storage and are opened through Android's share/open sheet.
- App lock and FLAG_SECURE keep covering every new screen.
- Uploads show the file name, size and course before sending, and need a tap to confirm. A submission cannot be sent by a
  background job.

## Sources (the app can use any of them)

1. **This phone, straight from the portal** (new): sign in with the enrollment number and password.
2. **Cloud checks** (today): reads `summary.json` from the student's private GitHub repository.
3. **Desktop** (today): the desktop app shares to the same repository.

## Phases (each one is released on its own)

| Phase | What | Needs a real phone test |
| --- | --- | --- |
| 1 | Portal session: sign-in, SSO, course list, errors (wrong password, campus, expired session) | yes |
| 2 | Dart parsers with fixture tests: assignments, attendance, exams, announcements, timetable, results | no |
| 3 | Refresh on the phone with the same views and reminders as today; background refresh every two hours | yes |
| 4 | Lectures page: list by course, download, open | yes |
| 5 | Assignments: download the brief, upload, replace and delete a submission | yes |
| 6 | The remaining desktop settings (there is no Activity page on the phone) | no |

## What I cannot check without the student

The portal sign-in and each page flow can only be proved against the real portal with a real account. Fixture tests prove
the parsing. Each phase therefore ends with a short checklist for a real phone.

Open risk: the portal may show a captcha or block automated sign-ins on a phone differently from the desktop. Phase 1 is
the first thing to test, because everything else depends on it.
