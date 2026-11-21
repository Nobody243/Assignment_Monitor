# Phone app changelog

## Unreleased

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
