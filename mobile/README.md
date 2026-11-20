# Assignment Monitor for phones

A Flutter app (Android first) that shows a student's deadlines, attendance, exams, timetable, results and announcements,
and reminds them. It reads one small file, `state/summary.json`, from the student's **own private GitHub repository**
(the one Cloud checks creates), so there is no server of ours and the portal password never reaches the phone.
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
- Sign-in with GitHub's device flow, offline cache, a stale-data banner, four palettes, light and dark.

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
flutter test --coverage                       # about 100 tests
python ../tools/dart_coverage.py --min 70     # coverage floor
python ../tools/dart_osv_check.py             # known vulnerabilities in the locked packages
python ../tools/make_mobile_icon.py           # redraws the icon and launch mark
python ../tools/make_mobile_fixtures.py       # rebuilds the awkward summary files the tests read
```

## Not done yet

Feeding the phone from a PC that does not use Cloud checks ("Share with my phone" on the desktop), a home-screen widget,
an app lock, iOS, and a store release (signing key). Notifications, the background check and the share sheet have not been
run on a real phone yet.
