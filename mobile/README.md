# Assignment Monitor for phones (prototype)

A Flutter prototype of the phone app, running on **fictional data** (`assets/summary.json`, made by
`python tools/make_summary.py mobile/assets/summary.json`). Read [DESIGN.md](DESIGN.md) first: what the phone is for, the
data contract (`summary.json`, built by `../summary.py` and served by the desktop engine at `/api/summary`), the screens,
notifications, security and the roadmap.

## Look at it

```bash
cd mobile
flutter run -d chrome        # in the browser (resize the window narrow, or use DevTools device mode)
flutter run -d windows       # as a window
flutter run                  # on a phone or emulator, if one is connected
```

Screens: **Today** (next deadline with a live countdown, Snooze and Done, today's classes, needs attention, announcements),
**Work** (filters, groups, detail sheet), **Attendance** (ring, hours you can miss, the whole-semester allowance, class by
class), **More** (Exams, Timetable, Results with the GPA and target calculator, Settings with reminder lead times, palettes
and light/dark). Screenshots are in `screenshots/`.

The prototype's clock starts at the moment the fixture was made, so countdowns look right whenever you open it.
Snooze, Done, palette and theme work; nothing is saved and nothing leaves the app.

## Checks

```bash
flutter analyze
flutter test                 # the grade and attendance arithmetic, same cases as the desktop app and the website
python ../tools/shoot_mobile.py out/   # screenshots after `flutter build web --release`
```

## Not built yet (see DESIGN.md, milestones M1 to M3)

Reading the real `summary.json` from the student's private repository (GitHub device flow, cache, freshness), local
scheduled reminders, push for new announcements and results, the desktop "Share with my phone" commit, the home-screen
widget, iOS.
