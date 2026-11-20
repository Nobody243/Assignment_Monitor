# Assignment Monitor for phones

A Flutter app (Android first) that shows a student's deadlines, attendance, exams, timetable, results and announcements,
and reminds them. It reads one small file, `state/summary.json`, from the student's **own private GitHub repository**
(the one Cloud checks creates), so there is no server of ours. With the desktop app the portal password never reaches the
phone; with the phone-only setup it is typed once, sealed and sent to the student's own GitHub secrets, and not kept
(see [SECURITY.md](SECURITY.md)).
Read [DESIGN.md](DESIGN.md) for the idea and the data contract, and [SECURITY.md](SECURITY.md) for what the phone holds,
what is checked, and what is still open.

## What it does

- **Today**: the next deadline with a live countdown (Snooze, Done), a tile grid (to do, overdue, attendance), what is
  coming up, today's classes, what needs attention, the latest announcements.
- **Assignments**: filters, groups, swipe right for Done and left for Snooze, a detail sheet.
- **Attendance**: an overall ring, hours you can still miss per course and for the whole semester, class by class.
- **Exams**: the next exam with room, row and seat, then the rest.
- **Announcements**: all of them, filter by course, new ones marked.
- **Timetable**: a day timeline with the gaps, a week grid, and save or share as PNG, JPG or PDF.
- **Results and GPA**: the transcript (CGPA, trend, every semester) and a calculator.
- **Reminders**: before each deadline (24 h, 3 h and 1 h by default), with Snooze and Done on the notification, quiet hours,
  a Sunday summary, a morning digest, and alerts for news while the app is closed. Calendar file of deadlines and exams.
- **Phone-only setup**: "I only use the phone" on the first screen sets up Cloud checks from the phone (private repository,
  schedule, encrypted portal login, first check), no desktop app needed. Settings, Cloud checks shows the last run and can
  run a check now, change the portal login or turn it off.
- Sign-in with GitHub's device flow, or with a fine-grained read-only token for one repository; offline cache, a stale-data
  banner, four palettes, light and dark, an optional app lock (fingerprint, face or PIN), a home-screen widget with the
  next deadline, a themed icon, and layouts for tablets and a phone on its side.

## Run it

```bash
cd mobile
flutter pub get
flutter run -d chrome     # a demo on fictional data, in the browser (no sign-in, no reminders)
flutter run               # on an Android phone or emulator, with real data
```

Pick "Look around with demo data" on the first screen to try it without signing in. CI (`.github/workflows/mobile-ci.yml`)
analyses, tests and builds a debug-signed APK on every change.

## Checks

```bash
flutter analyze
flutter test --coverage                       # about 170 tests
python ../tools/dart_coverage.py --min 70     # coverage floor
python ../tools/dart_osv_check.py             # known vulnerabilities in the locked packages
python ../tools/make_mobile_icon.py           # redraws the icon and launch mark
python ../tools/make_mobile_fixtures.py       # rebuilds the awkward summary files the tests read
```

## Not done yet

A run on real phones (notifications, the background check, the widget, the lock prompt and the share sheet have only been
tested in code), a store release (see [RELEASE.md](RELEASE.md) and [STORE.md](STORE.md)), and an iOS release (it compiles in
CI; Snooze, Done and the background check are Android only).
