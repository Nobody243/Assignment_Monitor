# Assignment Monitor for phones: design

Status: prototype with fictional data (this folder). Nothing here talks to a real portal or a real account.

## 1. What the phone app is for

The desktop app does the **watching**: it signs in to the portal, reads everything and raises alerts. A phone cannot do
that on its own (no background browser, iOS never), and the student's password should never live on a phone.

So the phone app is the **glance and nudge** surface:

- "What do I have to do next, and how long do I have?" answered in under three seconds, one-handed.
- Alerts that arrive where the student actually is: the phone.
- The numbers students check between classes: attendance margin, exam room and seat, today's classes, GPA what-ifs.

It is not a portal client, not a second place to type a password, and not where uploads happen in version 1.

## 2. Principles

1. **Answer first.** The first screen is the next deadline with a live countdown, not a menu.
2. **Thumb zone.** Navigation at the bottom; the main action of each screen reachable without stretching.
3. **Calm urgency.** Red only for "today" and "below the minimum". Everything else is quiet. No badges for the sake of badges.
4. **Honest freshness.** Always say how old the data is ("checked 40 min ago"), and say so loudly when it is more than a day old.
5. **Works offline.** The last summary is cached; every screen renders without a network.
6. **No secrets.** The phone holds a read-only token for one private repository. Never the portal password.
7. **Same look as the desktop app.** Same four palettes (Royal, Ink, Forest, Ember), same words, same number formats.

## 3. Architecture

```
 PC (desktop app)  --check-->  portal
        |  or
 GitHub Actions (cloud checks, PC off)
        |
        v   commits  summary.json  (one file, versioned schema)
 student's own PRIVATE repo  assignment-monitor-cloud
        ^
        |  read-only, HTTPS, conditional GET (ETag)
 Phone app  --> local cache --> screens, local reminders
        ^
        |  push for new announcements / results / extensions
 ntfy (no account, no infrastructure of ours)  or FCM later
```

- **`summary.json`** is the contract: everything a phone screen needs, already computed (countdowns are computed on the
  phone from absolute times; attendance margins, urgency groups and seat text are precomputed). Schema in
  `summary.py` (`SCHEMA_VERSION = 1`) and the fixture `assets/summary.json`.
- **Why a repo and not a server:** the project promises "no server, no account of ours". The cloud-check feature already
  puts the student's data in the student's own private repository, so the phone reads it from there.
- **Sign-in on the phone:** GitHub device flow (the same one the desktop uses): a code, approve in a browser. The
  stored token is kept in the platform keystore. Prefer a fine-grained, read-only token on that one repository; the
  prototype stays with fixtures until that is decided (open question 2).
- **Without cloud checks:** a student who only uses the PC can still pair: the desktop app commits `summary.json`
  to the same private repo after each check (a small "Share with my phone" switch). Same file, same phone app.

## 4. Information architecture

Bottom navigation, four tabs:

| Tab | Content |
| --- | --- |
| **Today** | Greeting and freshness. The next deadline as a hero card with countdown and "Snooze" / "Done". Today's classes strip. Needs-attention list (due today, overdue, attendance under the minimum). |
| **Work** | Assignments grouped Due today / Coming up / Later, filter chips (To do, Extended, Overdue, Submitted). Tap: detail sheet (course, due time, extension history, marks, files, Open in portal, Snooze, Done). |
| **Attendance** | One card per course: ring with the percentage, hours you can still miss or must attend, and the **whole-semester allowance** (credit-hour based) with hours used and left. |
| **More** | Exams (room, row, seat, countdown), Timetable (week grid), Results and a GPA / CGPA calculator with target mode, Settings (reminders, palette, light/dark, account, about). |

Why four: Today is the answer, Work and Attendance are the two lists students open between classes, and the rest are
visited rarely.

## 5. Key screens

**Today**

```
 Good afternoon, Alex            checked 40 min ago
 +----------------------------------------------+
 | DUE TODAY                              9h 32m|
 | Usability test report                        |
 | Human Computer Interaction  - 11:59 pm       |
 | [ Snooze 1 h ]            [ Done ]           |
 +----------------------------------------------+
 This week     Mon Tue [Wed] Thu Fri
 Needs attention
  ! 2 overdue assignments
  ! Database Systems: 70% attendance
```

**Work detail sheet**: a bottom sheet (drag to dismiss), the due time in large type, a time-left chip that turns
amber under 24 h and red under 3 h, an "extended from ..." line when the teacher moved the date, files listed
(download opens the portal's own link in the browser; the phone never downloads through our code), actions at the bottom.

**Attendance card**: ring + one sentence ("Safe: you can miss 4.3 h more"), then a compact block "Whole semester: you
can miss 12 h in total, 6 h used, 6 h left" with a thin bar. Tapping expands the class-by-class list.

**GPA calculator**: rows of course, credit hours, grade; result card pinned at the top; optional previous CGPA and
target. Same arithmetic as the desktop Results page and the website calculator (one grade scale, tested).

## 6. Notifications

- **Local reminders** scheduled on the device from `summary.json` (works with no network): 24 h, 3 h and 1 h before a
  deadline by default, user-selectable, never spoken, quiet hours 23:00 to 07:00 (delivered silently).
- **Snooze and Done** as notification actions. Snooze reschedules locally; Done hides reminders for that deadline.
  (Done never claims the portal agrees; the next check is the judge.)
- **Push** for events the phone cannot compute: new announcement, new result, deadline extended, seat posted. Via
  ntfy topics the student already pairs today; FCM later if wanted.
- **Sunday summary** and an optional **daily digest** reuse the desktop wording.

## 7. Visual design

- Palettes: the four desktop palettes mapped to Material 3 color schemes (`lib/theme.dart`); Ember is the default
  because it matches the website.
- Type: Geist (same as desktop) for text, tabular numerals for times and percentages.
- Shape: 20 px card radius, 28 px for the hero card, 56 px bottom bar, 48 px minimum touch targets, 16 px gutters.
- Motion: 200 ms ease for sheets and tab changes; reduced-motion respected; the countdown ticks once a minute
  (once a second under an hour).
- Accessibility: dynamic type up to 200%, TalkBack labels on every ring and chip, contrast checked per palette (the
  desktop palettes already pass AA).

## 8. Technology

- **Flutter 3** (Android first, iOS after), Dart. Riverpod for state, go_router for navigation,
  `flutter_local_notifications` + `workmanager` for reminders, `flutter_secure_storage` for the token,
  `http` with ETag caching. The prototype uses none of the plugins; it only needs Flutter itself.
- Android home-screen widget: "next deadline" (v1.1).
- iOS: push through APNs requires Apple's relay and a developer account; plan it after Android is stable.
- Distribution: Play Store (25 USD once). Direct APK from the website as the first, free channel.

## 9. Security and privacy

- Read-only access to one private repository; token in the Keystore/Keychain; sign out deletes it and the cache.
- No analytics, no crash reporting service. A "Copy support info" button (like the desktop one) strips personal details.
- Optional app lock (biometric) because the screen shows a student's grades and seat.
- The phone never sees the portal password and never contacts the portal.

## 10. Roadmap

| Milestone | Scope | Estimate |
| --- | --- | --- |
| M0 (done here) | Design, `summary.json` contract, Flutter prototype on fixtures | this prototype |
| M1 | Real read of `summary.json` from the repo (device flow, cache, freshness), Today / Work / Attendance, local reminders | 2 weeks |
| M2 | Exams, Timetable, GPA calculator, Settings, push via ntfy, Snooze / Done actions | 1.5 weeks |
| M3 | Desktop "Share with my phone" commit, widget, polish, Play internal testing | 1.5 weeks |
| M4 | iOS | later |

## 11. Open questions

1. Is a read-only phone app enough for version 1, or must a student be able to upload from the phone? (Upload needs the
   portal session; the honest options are a PC-side relay or a hidden WebView on Android only.)
2. Token scope: GitHub's device flow gives a classic token with the `repo` scope (broad). A GitHub App installed on
   the one repository, with "Contents: read", is the cleaner answer, at the cost of a small setup.
3. Should unpaired students get a view that works without any GitHub account at all (a QR from the desktop that
   hands over one signed file)? Simpler for students, weaker for freshness.
