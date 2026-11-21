# Phone app changelog

## Unreleased

- The four colour palettes now change the whole app: page and card surfaces, text and borders take the palette's tint (Royal is blue-grey, Forest green-grey, Ember warm, Ink neutral), and the bottom bar labels, progress bars and switches follow the accent. Contrast stays above AA in all eight light and dark themes.
- Results: the three summary cards (credit hours graded, courses graded, semesters done) are always the same height.
- Fixed the app staying on Android's still launch screen: the first screen now opens straight away, and reminders and the background check set themselves up beside it, each with a time limit.

## 1.0.1 - 2026-11-21

- Filter chips (Assignments, Announcements) and the remove-course button in the GPA calculator are 48 dp tall, the size Android asks for tap targets, and an accessibility test checks every screen for small or unlabeled controls.
- Phone and desktop releases are now automatic and separate: a change to `mobile/` is released as `phone-vX.Y.Z` once its checks pass.
