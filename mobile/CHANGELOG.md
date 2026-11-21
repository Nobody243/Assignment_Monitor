# Phone app changelog

## 1.0.2 - 2026-11-21

- The phone app can now work on its own, with no desktop app and no GitHub repository: sign in with your university login (enrollment number, password and campus) and the phone reads the portal itself. Your login stays in the phone's secure storage and goes only to the university portal.
- New Lectures section: the notes and files of every course, with a download that opens in your viewer or saves to your files.
- Assignments: download the brief, upload your work, replace or delete a submission, from the phone.
- The first screen has two equal choices named by what they give: "Full app" (signs in to the portal on the phone) and "Read-only viewer" (shows what your GitHub checks found, no portal password on the phone).
- With a university login saved, the background check (about every two hours) reads the portal itself and sends the same notifications as before; if the portal cannot be read it falls back to the GitHub copy when there is one.
- The four colour palettes now change the whole app: page and card surfaces, text and borders take the palette's tint (Royal is blue-grey, Forest green-grey, Ember warm, Ink neutral), and the bottom bar labels, progress bars and switches follow the accent. Contrast stays above AA in all eight light and dark themes.
- Results: the three summary cards (credit hours graded, courses graded, semesters done) are always the same height.
- Fixed the app staying on Android's still launch screen: the first screen now opens straight away, and reminders and the background check set themselves up beside it, each with a time limit.

## 1.0.1 - 2026-11-21

- Filter chips (Assignments, Announcements) and the remove-course button in the GPA calculator are 48 dp tall, the size Android asks for tap targets, and an accessibility test checks every screen for small or unlabeled controls.
- Phone and desktop releases are now automatic and separate: a change to `mobile/` is released as `phone-vX.Y.Z` once its checks pass.
