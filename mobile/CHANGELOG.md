# Phone app changelog

## 1.0.6 - 2026-11-21

- A progress bar under the top bar while the phone reads the portal, saying what it is reading and how far it has got ("Reading attendance · 2 of 7"), so a check that is still going can be told from one that has finished.
- The hidden browser now presents itself as a desktop browser, so the portal sends the same pages the readers were written for (a phone can be sent a different layout, which may be why lecture notes came back empty).
- The course list gets a second look, through single sign-on again, before the phone gives up with "No courses were found", which a lecture refresh could run into.
- Settings has "What the phone read": for each part, what came back and how long it took, and for an empty lecture page what the page was made of (counts only), with a Copy button.

## 1.0.5 - 2026-11-21

- Each screen now refreshes only itself: pull down (or tap the refresh button) on Assignments, Attendance, Exams, Announcements, Timetable, Results or Lectures and the phone reads just that part of the portal again, not everything. Today still does the full check, and so do the two-hourly background check and coming back to the app.
- Reading the portal is much faster: the phone used to ask the portal for a course and then start waiting for the page after it had already loaded, so every course sat out a long timeout. It now starts waiting before it asks, and does not wait at all for a page that updates in place.
- Each part now appears as soon as it is read (assignments first, then attendance, exams, results, timetable, announcements, lectures) instead of everything at the end, and a part that is not read yet keeps showing the last full read.
- A part or a single course that cannot be read no longer loses the rest, and the app says what is missing ("The portal did not give back: lectures. Pull down to try again.") instead of showing nothing. An empty lecture table gets one more look in case it filled in late.

## 1.0.4 - 2026-11-21

- The GitHub background-checks setup now explains, before GitHub's approval screen appears, that it will say "full control of private repositories" and "update GitHub Action workflows": what those words mean here, that GitHub cannot limit them to one repository, and how to remove the access afterwards.
- Signing in to the portal no longer needs a second try: the app waits until the portal's sign-in page and campus list are ready, checks the fields before pressing the button, and if the portal answers with no reason it tries once more from a fresh page. A wrong password still stops at once (the portal gives a reason), so it is never sent twice.
- The launch screen shows the same rounded orange tile as the app's own splash, instead of a hard-edged square, so the two look like one screen.
- A shorter, smoother start: the app's own splash screen now uses the same background as Android's launch screen (so they no longer flash between two colours) and stays for under a second unless the data takes longer to load.

## 1.0.3 - 2026-11-21

- The status bar (clock, battery and notification icons) is readable on a light page: it was drawing white icons on the light background. It now follows the theme in every palette, and the bottom navigation bar does too.
- Richer colours in the light themes: each palette has a clearer accent (Royal blue, Forest green, Ember orange) while the dark themes stay calm.
- The first screen has one main button: sign in with your university login. Someone who already uses the GitHub checks has a small link below it.
- Once the phone is working it offers, once, to let GitHub keep checking while the phone is off (free, in your own private repository). The portal login you already gave is reused, so it is not typed twice; Settings has the same option under Background checks.
- With a university login saved, the background check (about every two hours) reads the portal itself and sends the same notifications as before; if the portal cannot be read it falls back to the GitHub copy when there is one.

## 1.0.2 - 2026-11-21

- The phone app can now work on its own, with no desktop app and no GitHub repository: sign in with your university login (enrollment number, password and campus) and the phone reads the portal itself. Your login stays in the phone's secure storage and goes only to the university portal.
- New Lectures section: the notes and files of every course, with a download that opens in your viewer or saves to your files.
- Assignments: download the brief, upload your work, replace or delete a submission, from the phone.
- The four colour palettes now change the whole app: page and card surfaces, text and borders take the palette's tint (Royal is blue-grey, Forest green-grey, Ember warm, Ink neutral), and the bottom bar labels, progress bars and switches follow the accent. Contrast stays above AA in all eight light and dark themes.
- Results: the three summary cards (credit hours graded, courses graded, semesters done) are always the same height.
- Fixed the app staying on Android's still launch screen: the first screen now opens straight away, and reminders and the background check set themselves up beside it, each with a time limit.

## 1.0.1 - 2026-11-21

- Filter chips (Assignments, Announcements) and the remove-course button in the GPA calculator are 48 dp tall, the size Android asks for tap targets, and an accessibility test checks every screen for small or unlabeled controls.
- Phone and desktop releases are now automatic and separate: a change to `mobile/` is released as `phone-vX.Y.Z` once its checks pass.
