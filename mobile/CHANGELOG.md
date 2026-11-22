# Phone app changelog

## Unreleased

- A frozen hidden browser or a portal job that never ends can no longer hold every later job behind it (which showed as "Looking up your courses" for minutes and then nothing): each call into the hidden browser gives up after 45 seconds, a whole job after six minutes, and the next job then builds a fresh browser. The message says where it stopped.
## 1.0.9 - 2026-11-22

- The campus list is complete: Finishing School, National School of Hydrography and PN Nursing College were missing, so a student of those could not sign in; the list now matches the portal's own sign-in page exactly (a test pins it).
- A wrong password shows the portal's own sentence cleanly ("Error! Invalid credentials provided."), without the close symbol and stray spacing the portal's alert carries.
- University login no longer shows two back buttons side by side: Settings wrapped every page in its own app bar, and the pages that bring their own (University login, What the phone read, removing the login) ended up with two. Every Settings page now has exactly one, and a test checks it.
- The university sign-in is more patient and says more: it waits a few seconds for the sign-in form to appear before deciding the page is wrong, tries once more from a fresh page when it still looks wrong, tells you when the portal says the account is signed in somewhere else, and otherwise names what the page was (its title and field names, never anything typed) instead of "looks different". The sign-in test also no longer runs at the same time as another portal job on the one hidden browser.

## 1.0.8 - 2026-11-22

- Lecture downloads find their file more reliably: a list that is still filling in is read again a few times before the file is called missing, weeks and titles are compared loosely (case, spacing, a renumbered week), and a file is matched by name, then by its position in the week; a different week's file is never taken. The message names the course when it truly is not listed.
- Refreshing several times in a row no longer breaks the portal read: one hidden browser is reused (a new one each time piled up until the portal could not be read), and portal jobs (a read, a lecture list, a download) run one after another instead of signing in over each other.
- When a read fails, the red banner says why in a few words, and Settings, "What the phone read" keeps the reason.
- The phone is read-only by default again, and fast: your deadlines, attendance, exams, results and timetable are read from your desktop app or your own private GitHub repository (one small file, about a second), and notifications come from there too. The university-login-first start is gone from the first screen.
- The university login is now an add-on for lecture notes: add it in Settings, then Lectures lists every course's files and downloads them (about 20 to 30 seconds, only when you tap), and the assignment sheet can download a brief. It is not used for the rest of the data when GitHub is connected, and it can be removed in Settings.
- The phone no longer offers to upload, replace or delete a submission: submit on the portal or the PC app. (The code is kept but switched off.)
- The lecture list is kept when the data is refreshed from GitHub.
- A long value in the assignment sheet (a date with its time, a note) wraps instead of running off the edge.
- Attendance, exam seats and the timetable now arrive the first time: those portal pages draw their tables after they load, and the phone read them too early (an empty page that looked like "done"). It now waits until the table is there.
- A page that still comes back empty is read once more, and if it stays empty the earlier data is kept instead of being replaced by "no timetable yet"; the report in Settings says so.
- The everyday check is much shorter: lecture notes (two page loads per course) are read only when there are none yet or when you refresh the Lectures screen, and a course whose attendance hours have not changed keeps its class list instead of loading its page again.
## 1.0.7 - 2026-11-22

- The privacy statements are true again: the intro, the side menu and About and privacy said the portal password never reaches the phone, which stopped being true with the university login. They now say what each way of using the app keeps, and where it goes.
- Settings shows the real version (it said 1.0.0), and has "University login" for someone who came in through GitHub, so lectures and uploads can be added later. The Lectures screen points to it.
- Account and data is right for the Full app (it showed GitHub details), and has "Delete downloaded files"; signing out deletes them too.
- Empty screens can be pulled down to refresh (they could not be, though their message said to).
- A sign-in that cannot run (the hidden browser failing) now says so instead of leaving the spinner on.
- One strip under the top bar at a time (progress, else what is missing, else the GitHub offer), laid out so it cannot crowd out the content on a small phone or with large text; the offer waits for Settings on a very small screen.
- Showing a newly added login no longer hides the data you already have while the portal is read.
- Colours: the light Forest hero card is no longer neon, and Ink stays grey in both themes.
- Rules so the code shrinker cannot remove the hidden browser's download channel in the release build.
- Downloading a lecture file (and an assignment brief) now works: the file channel between the hidden browser and the app was added after the page had loaded, and Android only shows it to pages loaded afterwards, so the download script never reported back. It is now set up before any page loads, and a download that gets no answer from the portal stops after 25 seconds instead of waiting minutes.
- When a file action fails, the message now says why in a few words instead of only "check the connection".

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
