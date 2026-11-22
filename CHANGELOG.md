# Changelog

## Unreleased

- Clicking a desktop notification now opens the app (or brings it to the front if it is already running). The Snooze and Done buttons on reminders still work as before without opening a window.

## 1.9.8 - 2026-11-22

- The campus list in Settings is complete: Finishing School, National School of Hydrography and PN Nursing College were missing; it now matches the portal's own sign-in page.
- Update check: the app no longer says "you have the latest version" when a newer one exists. The phone app's releases share this repository, and once one of them became GitHub's "latest release" the updater read its number (1.0.8) as older than the app's (1.9.5). It now looks only at desktop releases (tagged v1.9.7), searching the release list when "latest" is not one, and the build marks each desktop release as the latest while phone releases never are.

## 1.9.7 - 2026-11-22

- Text follows the golden ratio: every size is the 14px body size times phi to a quarter-step (12.4, 14, 15.8, 17.8, 20.1, 22.7, 28.8, 36.7 px), and the line height follows the same ratio (airy for small text, tighter for headings). Nothing is below 12.4px now; the 10 and 11px labels were raised to it.
- The outlines of checkboxes, text boxes and dropdowns are clearly visible (about 3.5:1 against the page, in every theme and palette) instead of nearly invisible, and the keyboard focus ring is stronger.
- Built-in controls follow the theme (dropdown lists, autofill and date pickers are dark on a dark page) and checkmarks use the palette colour.
- Clickable things show the hand cursor.
- A dark-theme start no longer flashes a light window: the window colour behind the interface follows the theme you last used.
- Scrollbars are slim and match the app instead of Windows' wide grey bar: a rounded thumb floating in a transparent track with no arrow buttons, faint until you point at the area, wider and darker under the pointer, and tinted with the palette's accent while you drag it. It follows the light and dark themes.

## 1.9.6 - 2026-11-21

- Home: the two columns are balanced (the Results card moved under Courses), so there is no large empty block beside the long right-hand column. Text cut short with an ellipsis now shows in full as a tooltip when you point at it, and the small "View all" links have a larger click area.
- New `tools/audit_layout.py`: opens every page and Settings section at four window sizes and reports sideways scroll, dead space beside taller cards, fixed elements that scroll with the page, tiny click targets and clipped text. It reports nothing on the current build, with your real data.

## 1.9.5 - 2026-11-21

- Attendance and the two-column Settings sections now lay their cards out as two independent columns. Opening "Class by class" only pushes down the cards below it in its own column; the other column is neither stretched nor left with an empty gap beside the open card.

## 1.9.4 - 2026-11-21

- Lectures: the "selected / Download" bar is now a small pill fixed in the middle of the window, so scrolling and the sidebar never move it; it slides in and out, shows the count in a badge, and sits above the progress pill while something is running. Fixed underneath: every page was wrapped in a layer that made fixed elements scroll with the page.
- Checking the portal and downloading no longer show two progress indicators: the one at the bottom centre stays, the extra toast at the bottom right is gone (the toast now only appears when the action finishes, with the result).

## 1.9.3 - 2026-11-21

- Attendance: the whole "Class by class" row is the button (not just the small arrow), it opens and closes with a smooth slide, and opening it no longer stretches the course card beside it. The same treatment elsewhere: Settings, Notifications, "Advanced: mail server" is now a full-width row with an arrow and a slide; the semester tabs in Results and the Light/Dark switch in Appearance slide their highlight like the other tab strips.

## 1.9.2 - 2026-11-21

- The search palette (Ctrl+K) is larger and sized to the window: a wider box, bigger text, a taller list and a full-length hint in the search field.
- Update check on every launch: a few seconds after the app opens it looks for a newer version, and if there is one it says so with an Update now button (it asks before installing, as before). Still only for an installed build with update checks on.

## 1.9.1 - 2026-11-21

- Smoother interface: the highlight in the sidebar, the settings sections and every tab strip slides from item to item instead of jumping; pages enter from the side the sidebar item lies on; buttons give a short press response and can show a working spinner; menus open faster. The account menu now has real submenus (Theme, Palette with colour swatches) and shows its shortcuts (Ctrl B, Ctrl 9). Up and Down, Home and End walk the sidebar and the settings sections.
- Right-click an assignment row for a menu (open details, copy course and title, show only that course). Sidebar number badges pop when the count changes, loading placeholders shimmer, and switches have a springy thumb.
- Fixed: Ctrl+K (the search palette) crashed the window with "Something went wrong"; it opens normally again.
- Fixed: the Timetable page made the whole window scroll sideways in a narrow window; the timetable now scrolls inside its own card.
- New `tools/stress_ui.py`: a stress test that hammers navigation, menus, tabs, the command palette, the collapsing sidebar and resizing, then checks the interface is still consistent.

## 1.9.0 - 2026-11-21

- The Assignment Monitor phone app (Android) can read the same private repository, and it can also set up Cloud checks by itself, so the desktop and the phone each work on their own or together. Cloud checks now write `state/summary.json` for the phone.
- Share with my phone (Settings, Background): a PC that does not use Cloud checks can still feed the phone app. After each check that finds something new, the app writes one small file, `state/summary.json` (your deadlines, attendance, exams, timetable, results and announcement text), to a private repository `assignment-monitor-cloud` in your own GitHub account; the phone app signs in to the same account and reads it. Sign-in is GitHub's one-time code and asks only for the `repo` permission; the token is stored encrypted like your other secrets. The portal password never goes with it. A failed send never fails or slows a check (the reason shows in Settings), an unchanged summary is not sent again, Share now sends at once, and Turn off forgets the sign-in. If Cloud checks is on, it already shares the file, so the PC does not send it twice.

## 1.8.1 - 2026-11-20

- Dragging the mouse no longer highlights the whole window. Only text worth copying can be selected: what you type, announcements, activity log lines, file and folder names and error details. Buttons, menus, cards and tables stay clean.
- Back from the old app: F5 checks now, Ctrl+1…9 switch pages, Ctrl+F jumps to the page's filter box; an Extended filter on Assignments; Attendance can be filtered to below the minimum, close to the limit or on track; the tray menu has Check now.
- Attendance shows, next to the current percentage, how much you can miss over the WHOLE semester: 25% of the planned hours for the course's credit hours (a one-credit-hour lab of three hours a week, or 2 credit hours: 8 h, 3 credit hours: 12 h at a 75% minimum), with the hours used and left. If fewer classes are held, the limit is 25% of the hours actually held.
- A first-run setup like a code editor's walkthrough: welcome, sign in, look, reminders, automatic checks, files and finish, each step explained and skippable, and the whole setup skippable. It never appears for an existing sign-in; Settings, About can run it again.
- After the first successful sign-in the app offers (Yes/No) to turn on automatic checks.
- Deadline reminders at the lead times you choose (1 day, 12, 6, 3, 1 hour before; default 24, 3 and 1) as notification, voice (not between 23:00 and 07:00), phone and email, once per deadline, from the hourly background check.
- The tray icon and the taskbar button show a red dot when something is due within a day, and the tray tooltip says how many and what is next.
- Drop a file on an assignment row to upload it (with the usual confirmation); rows that cannot take a submission say why.
- Home shows the latest announcements again.
- Reminder notifications have Snooze 1 h and Done buttons (installed app): Snooze silences that assignment and reminds you once more when the time is up; Done stops reminders for that deadline (the portal still decides whether it is submitted, and a moved deadline reminds again).
- A Sunday-evening summary: what is due next week, exams, and attendance to watch. Switchable under Settings, Notifications.
- An optional daily digest: phone and email get one morning message instead of each alert, except alerts about something due within hours.
- Settings, About: Copy support info puts the version, which features are on and the recent log on the clipboard with enrollment numbers, emails, your Windows user name, your name and tokens removed, ready for a bug report.

- A Timetable page: your week as a grid with a colour per course, today and the current time marked, and Save as PNG, JPG or PDF (to Documents / Assignment Monitor).
- First run: a welcome with three steps (sign in, first check, automatic checks) instead of a dashboard that says you are all caught up.
- A notice on launch when a newer version exists (installed build, only if update checks are on), with a button to the update.
- The Results chart now scales its bars and uses your palette.
- Accessibility: every page passes axe-core in light and dark and all four palettes; status colours have enough contrast on light backgrounds, unlabelled controls are labelled, headings, lists and tabs are correctly structured, the sidebar is a navigation landmark, and no page scrolls sideways on a narrow window.

## 1.8.0 - 2026-11-18

- A new desktop interface (not a browser tab): a native window with the Home, Assignments, Attendance, Exams, Lectures, Announcements, Results and Settings pages, four colour palettes, light and dark, animations you can switch off, Yes/No confirmations, a not-found page, an engine-offline screen and an Activity log inside Settings.
- Background checks, reminders, shortcuts and the installer keep working: the command line (--check, --remind, --status, --test-alert, --enable-automation, --disable-automation, --disable-cloud, --quit, --tray, --view, --setup) is understood by the new app exactly as before.
- Install updates from Settings, About: the app downloads the new installer, checks it against the SHA-256 published with the release, and refuses it if it does not match.
- Security: the local engine needs a random key per launch and answers only the app's own window; requests are size-limited, wrong keys are slowed down, and responses carry no-sniff and no-referrer headers. The window runs sandboxed with a strict content policy, no web views, locked navigation, and Electron features the app never uses switched off.
- Checks in CI: types, lint, tests, build, dependency audit with signature verification, CodeQL, secret scan and dependency review.

## 1.7.0 - 2026-11-18

- Upload your work from the app. On the Assignments page a row the portal lets you submit gets **Upload**; a row with a submission gets **Replace** and **Delete**; a row past its deadline gets neither, because the portal decides (including deadlines extended only for those who missed). You choose the file, confirm what will happen, and the app fills in the portal's own Submit form, then reads the portal back to confirm. Replace checks the file, the course and the form first and only then deletes the old submission; if the upload fails after that, it tells you plainly. Files are checked before anything is touched: .pdf .doc .docx .xls .xlsx .zip, up to 15 MB; special symbols in the name are removed, as the portal asks. Manual only: never in the background and never in a cloud check.
- While an upload or delete runs, a progress card covers the window so nothing can be clicked, and closing the app waits until it has finished.
- Questions and results appear as small cards inside the window instead of Windows alerts here.
- Faster: the list is updated from the portal's own answer instead of re-checking everything, and signing in and opening a course wait less.
- Sign-in no longer sits out 30 seconds when the portal sends the single sign-on back to the login page.

## 1.6.2 - 2026-11-18

- Fixed: checks failing with "Timeout 45000ms exceeded ... waiting for locator("#courseId")" ("Checks are failing"). The LMS now re-issues the course list with fresh one-time values every time a course is opened, so the values read at the start were stale by the second course and the check waited out its timeout. The app now picks each course by name from the list as it is at that moment, for assignments, lecture notes, announcements and the downloads. Nothing changes in what is shown; if your checks were failing since the LMS update, the next one succeeds.

## 1.6.1 - 2026-10-25

- Settings are saved as changes on top of what is on disk, not as a whole snapshot: a window left open for hours (or a second copy of the app) saving its size no longer puts its stale copy of the GitHub sign-in or the phone pairing back over a newer one.
- Security lint: every URL the app opens is checked to be https first; content hashes declare they are not security hashes; Bandit runs in CI beside ruff.
- Website: valid HTML on every page (the no-script style moved to the head), larger tap targets on the feature dots.
- Running the app from the source tree next to an installation no longer takes over the installed app's background tasks and shortcuts (they now stay with the installed program), and the test suite runs in a throw-away data folder with alerts, channels, update checks and task registration switched off. A source-tree run had re-pointed the tasks and the Desktop shortcut at the source, which opened a copy of the app with none of the student's setup.
- Settings: the cloud-checks texts say the real schedule (07:43 and 18:37) instead of 8 AM and 7 PM; the data folder is shown as %LOCALAPPDATA%\Assignment Monitor when it lives there.
- Start-up race fixed: the Settings page's cloud-status worker could call into the window before the main loop was running, and the error ("main thread is not in main loop") landed in the status bar. The worker now waits for the loop.

## 1.6.0 - 2026-10-25

- Results page: your transcript one semester at a time, read from the CMS Provisional Result page. A strip with the CGPA, credits earned and semesters graded, a semester bar with each semester's GPA, and below it the chosen semester. For the running semester, a calculator: pick the grade you expect in each course and see the projected GPA and CGPA, a row of same-grade scenarios (every course at A, A-, B+ ... and where the CGPA lands), and a target CGPA with the semester GPA it needs and the lowest grade that gets there, or a plain "not reachable this semester". For a past semester, the grades with the portal's GPA and CGPA at the time, and Try other grades to see how a different grade in any course would have moved the CGPA. Nothing is saved; Reset what-ifs puts the real transcript back. The arithmetic matches the portal's own figures (checked against a real six-semester transcript). The moment a result is posted, whole or course by course, a notification goes out, phone and email too; the first read after this update stays quiet. Switchable under Settings → Campus tracking; cloud checks read it too.

## 1.5.12 - 2026-10-24

- Cloud checks now reach the phone and the mailbox. The run handed the sends to a background thread and exited as soon as the check was done, so they were cut off before they went out; the test alert at set-up was sent directly, which is why it arrived. Deliveries in the cloud now happen before the run finishes.
- "All caught up" after a check stays a desktop notification; it is no longer pushed to the phone or emailed twice a day.
- Cloud checks are scheduled at 07:43 and 18:37 Pakistan time instead of 08:00 and 19:00. GitHub starts jobs set to the top of the hour hours late (the user's runs landed at 12:50 and 22:15); odd minutes are picked up within minutes. Takes effect the next time Set up is pressed under Cloud checks.
- The website moved to https://assignment-monitor.saaddev.top. New phone pairings and the links the app opens use the new address; the old vercel.app address redirects to it, except the phone page, which keeps serving phones that were paired before the move.

## 1.5.11 - 2026-10-24

- No more ghosting when the window is maximized, restored or resized: while the size changes the window sits behind a plain backdrop, and once it is still the finished page fades in. Tk paints each widget in its own time, so the old and the new layout used to show on top of each other for a tenth of a second.
- Assignments: each row offers the files the portal has for it, the teacher's brief, your own submission, your returned work and a posted solution, downloaded with one click into the Lectures folder under course / Assignments. Download briefs fetches the brief for every assignment in the current list. Links are re-read at download time (they expire daily), existing files are skipped.
- A solution file posted, or work returned with comments, is announced after a check like other changes (notification only).
- Lectures: while a download runs, Stop takes the place of Select all and Clear, so it is never cut off; the folder path shows its last two parts when long.

## 1.5.10 - 2026-10-24

- Lectures: a week with several files now downloads all of them. Files were matched to the portal's fresh links by week, title and label, and every file in a week carries the same label ("Download Lecture"), so all of them resolved to the last one: the same file was fetched twice and the copy skipped as already present. Matching is now by file name first. Select the weeks again and press Download selected; files already on disk are skipped and the missing ones arrive.

## 1.5.8 - 2026-10-24

- Check for updates no longer depends on the GitHub API, which allows only 60 unauthenticated requests an hour per address and is easily used up by other tools on the same network; when that happened the check "failed" and opened the releases page in a browser instead of updating. The check now reads the release tag from GitHub's own redirect (no limit, no token), derives the installer's address from it, and falls back to the API only if that fails. If GitHub really cannot be reached, the app says so and stays put; nothing opens in a browser.

## 1.5.7 - 2026-10-24

(1.5.6 was tagged but never published: its release build hung in the new GUI test, fixed here. Same changes.)

- Lectures: pressing Download selected no longer fails with "window isn't packed" (the progress bar was placed relative to the wrong frame). Reported through the new crash dialog within a day of it shipping.
- A GUI smoke test now opens the real window on throwaway data, draws every page and runs the download path, so this class of error is caught before a release.
- Clickable Dashboard cards no longer raise an error when Tk delivers the click binding without an event (seen once during a full live test; it showed as a crash dialog, nothing else).
- Verified end to end on a real account: sync, every page and filter, timetable export in three formats, a real lecture download, voice preview, test alert, sign-in verification, test email, test push, calendar file, preferences, automation off and on, start-with-Windows, update check, theme switch, tray, keyboard shortcuts.

## 1.5.5 - 2026-10-23

- On a PC without Google Chrome, the first check no longer fails with "Sign-in failed: This LinkedIn profile is already associated with another student." The sign-in had in fact succeeded; the downloaded browser engine was a moment slower to leave the login page, and the app judged too early, quoting a hidden notice from that page. It now waits for the portal's redirect, reads only visible messages, and prefers the full Chromium engine over the headless shell. Found by a new clean-machine install test that runs the release on a fresh Windows with Chrome hidden.
- The sign-in window fits small screens: the card, its text and the theme switch follow the window, and the gaps tighten on short windows (a 1366x768 laptop at 125 % scaling). The main window also leaves less of the screen unused on such laptops.
- The enrollment number no longer appears in the log (the sign-in line shows its last three characters), since logs get pasted into issues.

## 1.5.4 - 2026-10-23

- Between semesters: when the portal lists no courses yet, every page says so instead of showing last semester's data, alerts pause after one notice, and everything fills in on the first check after registration. Announcements from an earlier semester are cleared once the new one has data.
- Failed background checks are counted, not announced one by one: a portal outage is reported after three failures in a row (and every third after that), a rejected sign-in once. The Dashboard's "Last sync" line shows how many checks have failed since the last good one.
- A "Something went wrong" dialog for errors inside the window, with Copy details, Open log and a pre-filled GitHub issue (app version, Windows version and the error lines; nothing else). Until now such errors were invisible in the packaged app.

## 1.5.3 - 2026-10-23

- Uninstalling with cloud checks on now offers to turn them off, so your portal login does not stay in a GitHub workflow that keeps running after the app is gone. Silent uninstalls leave the cloud alone. The same is available from the command line as `--disable-cloud`.

## 1.5.2 - 2026-10-23

- Pillow updated to 13.0.0, which closes eight published vulnerabilities in the image library (CVE-2026-96636 to 96644 and GHSA-78g4-xqwv-q3g8); the dependency audit is clean again.
- Third-party licence notes list PyNaCl and libsodium, used since 1.5.0 to seal the cloud-check secrets.
- Website: robots.txt and sitemap.xml, canonical and per-page social tags, structured data for the app, a current social card, a 180 px touch icon, and the GitHub repository's description and topics.

## 1.5.1 - 2026-10-23

- When the last three cloud checks have failed, the PC shows one desktop notification pointing at Settings > Cloud checks and the Actions page (checked when the app opens and after the PC's own daily check; one notification per streak).
- The cloud workflow commits a timestamp on every run, because GitHub switches off the schedule of a repository that has had no commits for 60 days, which a quiet semester break would have triggered. Existing cloud setups receive the new workflow automatically.
- Website: a Cloud checks walkthrough page with screenshots of every step.

## 1.5.0 - 2026-10-23

- Cloud checks: alerts with the PC off. Settings → Cloud checks sets up, after a consent screen and a one-time GitHub code, a private repository in your own GitHub account whose workflow runs the same check at 8 AM and 7 PM on GitHub's machines and sends the phone and email alerts. Your login and channel keys go there as GitHub Actions secrets, sealed on the PC with the repository's key; the PC's cache is copied so the cloud knows what is new; settings changed on the PC follow automatically; an app update moves the workflow to the new version; the PC keeps desktop and voice alerts and leaves phone and email to the cloud so nothing arrives twice. Turn off removes the secrets and the workflow. No server of ours is involved. Run now and the last result are shown in Settings.
- Settings can be given as `AM_<KEY>` environment variables (how the cloud runner receives them).

## 1.4.6 - 2026-10-23

- The background checks now suit a laptop. The 7 PM check wakes a sleeping or hibernating PC, runs on battery (before, Windows skipped it whenever the charger was out and killed it if you unplugged mid-check), runs as soon as the PC is back if 7 PM was missed, and retries up to three times, ten minutes apart, if the portal was unreachable. The hourly reminder and the sign-in catch-up also run on battery; the hourly one never wakes the PC. Tasks created by an earlier version are re-registered with these settings the first time the app opens. A PC that is shut down still checks nothing; see the website's FAQ.
- Reading a page no longer fails with "page is navigating and changing the content" when a course change is still loading on a slow connection; the read waits and retries.

## 1.4.5 - 2026-10-23

- Phone pushes work. Every push, including the test after pairing, failed with "could not deserialize key data": the signing key the PC generates is stored as PEM text, and the push library only accepts a key given as text when it is a file path or a bare base64 key. The key is now loaded and handed over as an object. Nothing to redo: the pairing and the stored keys were fine.

## 1.4.4 - 2026-10-23

- The Pair a phone dialog explains itself: three numbered steps (open the Camera app, point it at the code, tap Allow on the page), a status line that changes to "your phone opened the page, now tap Allow" the moment the link is opened, and two ways round a camera that will not scan: Copy link, or Email me the link when email is set up. The link stays valid for ten minutes.
- Pairing on a mobile network no longer fails with "the relay answered 429": the relay rate-limits by public address and carrier networks put thousands of phones behind one. The phone page now waits the relay's suggested time and retries, then moves on to three other public relays, and the PC watches all of them.

## 1.4.3 - 2026-10-23

- Pages cross-fade into each other. Tk cannot fade hundreds of widgets, so the app photographs the page it is leaving and the one it is opening and blends the two pictures over the page area; one image moving is smooth where moving every widget never was. Off with the Animations switch.
- Long lists are built in parts: the Lectures, Assignments, Attendance and Announcements pages create the first screenfuls of rows at once and the rest as you scroll towards them, so a heavy page opens in a fraction of the time and repaints faster while it scrolls. Ctrl+End builds the rest first.
- Lighter rows: the week, assignment, class and announcement rows are one frame with a grid inside instead of frames nested three deep, and separators are plain lines rather than drawn canvases; a page of ninety weeks has a few hundred fewer widgets.
- Pages open in about half the time: CustomTkinter's scrollbar redrew itself and forced every pending layout to finish for each widget added to a list; it is now updated once per idle cycle.

## 1.4.2 - 2026-10-22

- Faster, calmer window: pages are rebuilt only when the data or settings behind them changed (the dashboard also once a minute for its countdowns), and they are built before they are shown, so switching between pages is instant and a page no longer assembles itself on screen; the page slide-in is gone because it re-laid out every widget for a dozen frames; the remaining animations run at 30 frames a second.
- Smoother scrolling: wheel events are gathered and applied once per frame instead of repainting the page for every one of the burst a precision wheel or touchpad sends, each step waits for its repaint before the next lands (the striped, half-drawn text while scrolling fast came from steps landing on a page that was still painting), and a notch moves 40 px instead of 20.
- The wheel scrolls a page anywhere on it, including over the toolbar above the list on Assignments, Attendance, Timetable, Announcements and Lectures. PageUp / PageDown scroll by a screen, Ctrl+Home / Ctrl+End jump to the ends.
- Website: screenshots retaken from this build and the dashboard tour re-aimed at the cards, which had moved down when today's classes joined the page.

## 1.4.1 - 2026-10-22

- Fix: the Dashboard, Exams and Settings pages could not be scrolled and their content was pinned to the window height (since 1.3.1, when the page slide-in started reconfiguring the wrong frame). Settings is reachable to the bottom again.
- Fix: the Timetable page's own scroll region was being replaced by its resize handler.
- Smoother fast scrolling: hover highlights pause while the wheel is turning, so rows sliding under the pointer no longer trigger a redraw storm that tore the text.

## 1.4.0 - 2026-10-22

- Alerts on your phone and in your inbox. Settings → Phone, email and calendar: link your own mailbox (Gmail, Outlook, the university's Microsoft 365 or any SMTP server) with an app password, and pair a phone by scanning a QR code; no app to install, no account, and nothing passes through a server of ours. Every alert the app already raises on Windows is delivered to the linked channels too.
- Calendar: an .ics file of deadlines and exams in Documents › Assignment Monitor, rewritten after every sync, and optional emailed calendar invites that appear in Google Calendar or Outlook on the phone. Both off until you turn them on.
- Timetable: the CMS week drawn as a clean grid, in the app and saved as PNG, JPG or PDF. Today's classes on the dashboard with the one happening now highlighted.
- Miscellaneous files: the LMS Miscellaneous page of every course (project briefs, templates, past papers) under a toggle on the Lectures page, downloadable like lecture notes into course / Miscellaneous folders.
- Attendance: the first read of a new file kind never fires alerts for files that were already there.

## 1.3.3 - 2026-10-22

- Attendance page rebuilt as one list of every registered course, weakest first, with filters for courses under the minimum, at risk and on track. Click a course for its classes, or switch the page to every class or only the missed ones.

## 1.3.2 - 2026-10-22

- New colour scheme in both themes: cool slate greys with a single indigo accent, calmer state colours, and a sidebar and status bar a shade off the page so the shell frames the content. Pills are fully rounded and nav items a little softer.

## 1.3.1 - 2026-10-22

- Design pass: rounded surfaces that lift on hover, a short slide when switching pages, a fade when switching themes, counters that count up and attendance bars that fill in. All of it can be switched off with the new Animations switch in Settings, Appearance.
- Faster: fonts are built once and reused instead of being created for every label, so pages open quicker and use less memory.
- Sign-in screen copy covers everything the app watches.

## 1.3.0 - 2026-10-22

- Lectures: every course's lecture notes in one list, by week, with a checkbox per file. Tick what you want and "Download selected" fetches the files through the app's own sign-in into a folder you choose (Documents / Assignment Monitor / Lectures by default), organised as course / week - title. Files already on disk are skipped; video links open in the browser.
- A notification when new lecture notes are uploaded (switchable, like the other trackers).
- Attendance, exam and announcement alerts are Windows notifications only; the voice is kept for assignment reminders.

## 1.2.0 - 2026-10-21

- Attendance: every course's present, absent and total hours with the percentage, how many hours you can still miss (or need to attend) for the minimum you set, and the class-by-class record with topics. An alert when a new absence is recorded or a course drops under the minimum.
- Exams: the seating plan with date, session, time, room, row and seat for every paper, a countdown on the dashboard, a reminder the day before (configurable) and once on the morning of the paper, and an alert when the plan is posted or a room changes.
- Announcements: every course's LMS announcements in one place, newest first, with an alert for each new one.
- Three new pages (Attendance, Exams, Announcements), dashboard cards for attendance and the next exam, and a Campus tracking section in Settings to switch each one on or off and set the attendance minimum.
- One signed-in session now reads everything; a page that cannot be read is skipped and logged instead of failing the sync.
- `--status` prints attendance and upcoming exams as well as assignments.

## 1.5.9 - 2026-10-24

- The Timetable page shows its Save-as buttons only when there is a timetable to save.
- The Dashboard's Next deadline card says "Yesterday" or "3 days ago" for an overdue item instead of "-1 days".
- The sidebar is the eight pages a student uses; the activity log moved under Settings → Your data (and opens from the Dashboard's "checks failed" line). Same log, one click further from the places where nobody needs it.
- Settings → Your data: Activity log, Open data folder, and Reset local data (last, confirmed). Settings → About: the update check shows its result beside the button, and What's new opens the release notes.
- Typography: the app now ships the Inter typeface (regular, medium, semibold and a display cut for headings) with Segoe UI as the fallback, on a golden-ratio type scale. Nothing is set in bold any more; headings are semibold.
- Colour: the accent and every status colour (due today, soon, this week, submitted, extended) sit one golden angle apart on the colour wheel, in both themes, and all pass AA contrast.
- Website: same Inter typography and golden-ratio heading scale, no italics; the Download button in the nav opens a chooser (installer, portable zip, guide); phones, Macs and Linux get "Send to your PC" instead of a 60 MB installer they cannot run; the changelog page is gone (release notes live on GitHub).

## 1.1.0 - 2026-10-20

- New app icon (dial with a deadline ping) across the app, installer, tray and website.
- Voice settings: choose the Windows voice, volume and speaking rate for spoken reminders, with a test button.
- Uninstalling now removes everything: running copies are closed, the scheduled tasks and Startup entry are unregistered, and you are asked whether to delete the saved sign-in and cached data.
- Installer and workflow are ready for SignPath code signing (used automatically once the project is approved).
- Website: https://assignment-monitor.vercel.app

## 1.0.0 - 2026-10-19

- First release: dashboard, assignments, settings and activity pages; light and dark themes; tray mode.
- Background checks through Windows Task Scheduler (daily, hourly reminders, at sign-in).
- Spoken and toast reminders on due days; extended-deadline detection.
- In-app updater that checks numbered GitHub releases.
- Per-user installer (no administrator rights) and a portable zip.
