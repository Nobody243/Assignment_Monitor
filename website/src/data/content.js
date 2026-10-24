import { REPO_URL } from "../lib/release.jsx";

export const LINKS = {
  repo: REPO_URL,
  issues: `${REPO_URL}/issues`,
  releases: `${REPO_URL}/releases`,
  readmeSource: `${REPO_URL}/blob/main/README.md#run-from-source`,
  privacy: `${REPO_URL}/blob/main/PRIVACY.md`,
  security: `${REPO_URL}/blob/main/SECURITY.md`,
  signing: `${REPO_URL}/blob/main/CODE_SIGNING_POLICY.md`,
  thirdParty: `${REPO_URL}/blob/main/THIRD_PARTY_LICENSES.md`,
  license: `${REPO_URL}/blob/main/LICENSE`,
  changelog: `${REPO_URL}/blob/main/CHANGELOG.md`,
};

export const TICKER = [
  "Checks every evening at 19:00, waking a sleeping laptop", "Catch-up check after you sign in", "Hourly voice reminder on due days", "Catches extended deadlines",
  "Attendance margin per course", "Exam room and seat, with a countdown", "Course announcements in one feed", "Lecture notes, downloaded into tidy folders", "Timetable as a clean PNG or PDF", "Alerts on your phone and in your inbox", "Runs in the tray, no window needed",
  "Islamabad · Lahore · Karachi campuses", "Nothing sent anywhere but the portal",
];

export const NUMBERS = [
  { value: 19, suffix: ":00", text: "Automatic check every evening, plus a catch-up when you sign in" },
  { value: 60, suffix: " min", text: "Between voice reminders while an unsubmitted assignment is due today" },
  { value: 6, suffix: " things", text: "Watched for you: assignments, attendance, the exam seating plan, announcements, lecture notes and the timetable" },
  { value: 3, suffix: " campuses", text: "Islamabad, Lahore and Karachi. Pick yours at sign-in; nothing of yours leaves your PC" },
];

export const TOUR = [
  { spot: [19.6, 17.6, 76.8, 15.6], label: "Next deadline", title: "The next deadline, with a countdown", text: "Whatever is due soonest and still unsubmitted sits at the top, coloured by urgency. Today is red, this week is amber, later is quiet." },
  { spot: [19.6, 33.6, 76.8, 11.4], label: "Six counters", title: "Pending, due today, this week, extended, overdue, submitted", text: "Each counter is a filter. Click it and the Assignments page opens on exactly that slice." },
  { spot: [19.6, 45.4, 76.8, 24.8], label: "Today's classes", title: "Today's classes, the one happening now highlighted", text: "Read from the CMS timetable: what is next, where, and when. The Timetable page behind it draws the whole week and saves it as a picture." },
  { spot: [19.9, 70.8, 44.8, 24.6], label: "Attendance", title: "Your attendance margin, weakest course first", text: "Every course's percentage from the CMS. Red is under the 75% rule; the Attendance page behind it says how many classes you can still miss, or must attend." },
  { spot: [65.6, 70.8, 30.6, 24.6], label: "Next exam", title: "Room and seat before you have to ask", text: "The seating plan from the CMS with a countdown, time, room, row and seat. A notification comes the day before and on the morning of the paper." },
  { spot: [1, 2.5, 16, 96], label: "Always a click away", title: "Light or dark, tray or window", text: "Switch the theme any time. Close the window and it keeps running in the tray; the background checks run even when it doesn't." },
];

export const FEATURES = [
  { n: "01", tag: "Deadlines", title: "Catches extended deadlines", text: "When a teacher moves a date, the LMS squashes old and new into one string. The app reads both and flags the change.", datestr: { now: "4 October 2026 - 11:50 am", was: "13 September 2026-11:55 am" } },
  { n: "02", tag: "Reminders", title: "Reminds you out loud", text: "On the day something is due and still unsubmitted, a spoken reminder and a Windows notification every hour until it's done. Pick the voice, volume and speed." },
  { n: "03", tag: "Attendance", title: "Knows your attendance margin", text: "Every course's hours and percentage from the CMS, how many classes you can still miss for the 75% rule, and a notification the day an absence is recorded.", list: [["Under minimum", "needs 10 h present"], ["At risk", "can miss 1 h"], ["On track", "can miss 6 h"]] },
  { n: "04", tag: "Exams", title: "Carries your seating plan", text: "Date, session, time, room, row and seat for every paper, a countdown on the dashboard, and a notification the day before and on the morning of the exam." },
  { n: "05", tag: "Announcements", title: "Reads every course's notices", text: "Announcements from all your course pages in one feed, newest first, with a notification for each new one. Deadline extensions are often posted here first." },
  { n: "06", tag: "Lectures", title: "Collects your lecture notes", text: "Every course's notes in one list by week, and its Miscellaneous files under a toggle. Tick the files you want and they download through the app's own sign-in into course / week folders; what you already have is skipped." },
  { n: "06b", tag: "Assignment files", title: "Keeps the assignment itself", text: "Each assignment row offers the teacher's brief, your own submission and your returned work, one click each, saved under course / Assignments. Deleted your submission from the PC? It is one click away again. A solution file or returned work from the teacher is announced like everything else." },
  { n: "07", tag: "Timetable", title: "Draws your week properly", text: "The CMS timetable as a clean grid: one row per day, a colour per course, room and teacher on every block. In the app, and saved as PNG, JPG or PDF for your lock screen or a print." },
  { n: "08", tag: "Phone", title: "Reaches your phone and inbox", text: "Pair a phone by scanning a code, no app and no account, and link your own mailbox with an app password. Every alert arrives there too." },
  { n: "09", tag: "Calendar", title: "Puts deadlines on your calendar", text: "An .ics of deadlines and exams kept up to date on your PC, and, if you want, calendar invites by email that land in Google Calendar or Outlook on the phone. Off until you turn it on." },
  { n: "10", tag: "Automation", title: "Runs itself", text: "Three Windows tasks under your own account. No admin rights, no service, and they work with the window closed, on battery, and from sleep.", list: [["Daily check", "19:00, wakes the PC"], ["Catch-up check", "2 min after sign-in"], ["Due-today reminder", "hourly"]] },
  { n: "11", tag: "Tray", title: "Lives in the tray", text: "Close the window and it keeps running quietly. Right-click the icon to open, sync now, or quit. Optionally starts with Windows." },
  { n: "12", tag: "Updates", title: "Updates itself, safely", text: "Checks the project's GitHub releases on start (switchable). One click downloads the new installer, closes, reinstalls and reopens. Your sign-in and data are kept." },
  { n: "13", tag: "Source", title: "Open, auditable, yours", text: "MIT licensed. Every release is built by GitHub Actions from the public repository, with tests and a dependency audit on every commit." },
  { n: "14", tag: "Cloud", title: "Checks with the PC off", text: "Optional. One GitHub sign-in and the same check runs at 8 AM and 7 PM on GitHub's machines, from a private repository in your own account, and alerts your phone and inbox. Free, no server of ours, off until you turn it on. Walkthrough on the Cloud page.", list: [["Where", "your GitHub account"], ["When", "08:00 and 19:00"], ["Cost", "free"]] },
];

export const STEPS = [
  { title: "Install", text: "Run the setup. It installs for your user account only, no administrator password, and adds a Start Menu and Desktop icon." },
  { title: "Sign in once", text: "Enrollment number, CMS password, campus. The app verifies the sign-in live and reads every course of the semester." },
  { title: "Let it run", text: "Leave \"Check automatically\" ticked. From then on it checks at 7 PM, after you sign in to Windows, and hourly on due days." },
];

export const SHOT_V = "143";
export const shot = (id, theme) => `/assets/shot-${id}-${theme}.png?v=${SHOT_V}`;

export const SCREENS = [
  { id: "dashboard", label: "Dashboard", caption: "Dashboard: next deadline, counters, attention list, course progress." },
  { id: "attendance", label: "Attendance", caption: "Attendance: every course's hours, the margin to the 75% rule, and the class-by-class record." },
  { id: "exams", label: "Exams", caption: "Exams: the seating plan with room, row and seat, and a countdown to each paper." },
  { id: "timetable", label: "Timetable", caption: "Timetable: the week as a clean grid, one row per day and a colour per course; save it as PNG, JPG or PDF." },
  { id: "lectures", label: "Lectures", caption: "Lectures: every course's notes by week; tick files and download them into course / week folders." },
  { id: "announcements", label: "Announcements", caption: "Announcements: every course's notices in one feed, newest first." },
  { id: "assignments", label: "Assignments", caption: "Assignments: filters, course picker, search, extension history and marks." },
  { id: "settings", label: "Settings", caption: "Settings: account, theme, tray, voice and notifications, phone, email and calendar, campus tracking, automatic checks, privacy." },
  { id: "setup", label: "Sign-in", caption: "First run: sign in once, tick automatic checks, done." },
];

export const PRIVACY_CARDS = [
  { tag: "Encrypted by Windows", title: "DPAPI, your account only", text: "The portal password is protected with Windows Data Protection for your user account. Another user or another PC cannot read it, and it is never written to the log." },
  { tag: "Two hosts, HTTPS", title: "Talks only to the portal", text: "The only connections are to cms.bahria.edu.pk and lms.bahria.edu.pk, plus an optional, switchable check of GitHub for new versions. Phone and email alerts, if you turn them on, go from your PC to your own mailbox and your phone's browser; this site runs no server and keeps no accounts. No analytics, no telemetry." },
  { tag: "Read the code", title: "Open source, built in public", text: "MIT licensed. Releases are built by GitHub Actions straight from the repository, and you can build the same thing yourself with one command." },
  { tag: "Optional cloud", title: "Your account, not ours", text: "Cloud checks, if you turn them on, keep your login as encrypted secrets in a private repository in your own GitHub account and run there. The app tells you exactly what goes where before you agree, and turning it off removes it." },
];

export const FAQ = [
  { q: "Windows says \"Windows protected your PC\". Is it safe?", a: "Yes. The warning appears because the installer is not yet code-signed; the project is applying for a free open-source certificate. Click \"More info\", then \"Run anyway\". If you prefer, build it yourself from the source code with one command; the result is identical." },
  { q: "Is this an official Bahria University app?", a: "No. Assignment Monitor is an independent student project. It is not affiliated with, endorsed by, or supported by Bahria University." },
  { q: "What does it do with my account?", a: "It signs in with your own credentials and reads your own pages, the same way you would in a browser: the LMS assignments, announcements, lecture-notes and Miscellaneous-files lists, and the CMS attendance, exam seating plan and timetable. Each can be switched off in Settings. Files (lecture notes, an assignment's brief, your own submission, returned work) are downloaded only when you click Download for them, to a folder you choose. It never submits, uploads or changes anything on the portal, and it never sends your data anywhere." },
  { q: "What happens between semesters?", a: "While the portal lists no courses (registration not done yet) every page in the app says so and alerts pause after one notice. Nothing is deleted; the pages fill in on the first check after your courses appear, and announcements from the previous semester are cleared then." },
  { q: "Do I need Google Chrome?", a: "If Chrome is installed it is used in the background. If not, a browser engine is downloaded once automatically. You never see a browser window." },
  { q: "Which alerts are spoken?", a: "Only assignment reminders use the voice: the due-today reminder and the after-sync summary. Attendance, exam and announcement alerts are ordinary Windows notifications, and every category can be switched off in Settings." },
  { q: "How do alerts reach my phone without an app?", a: "Through the phone's browser. In the app press Pair a phone, scan the code with the phone's camera, tap Allow on the page that opens, done. Pushes then go straight from your PC to the phone's browser push service, encrypted end to end; the website only passes the phone's address to your PC once, encrypted, during pairing. Android works with Chrome or Samsung Internet; iPhone needs iOS 16.4 or newer and the page added to the Home Screen. No VPN, no Telegram, no WhatsApp, and it costs nothing." },
  { q: "Which email accounts work?", a: "Any mailbox with SMTP: Gmail, Outlook, the university's Microsoft 365 account, Yahoo, iCloud or your own server. The app sends from your mailbox to itself using an app password, which is stored encrypted on your PC. The Advanced button sets the server by hand when the guess is wrong." },
  { q: "Does my PC need to be on at 7 PM?", a: "On or asleep. The 7 PM check wakes a sleeping or hibernating laptop, runs on battery, and if the PC was shut down it runs as soon as you are back, plus a catch-up two minutes after you sign in. The hourly reminder never wakes the PC; it only fires while something is due that day. For alerts while the PC is fully off, turn on cloud checks." },
  { q: "Can it alert me while the PC is off?", a: "Yes, with cloud checks. In Settings press Set up under Cloud checks, read what it will do, and sign in to GitHub with the one-time code shown. The app creates a private repository in your own GitHub account, stores your login and channel keys there as encrypted secrets, and installs a workflow that runs the same check at 8 AM and 7 PM on GitHub's machines and alerts your phone and inbox. It is free (a check uses two or three of GitHub's 2,000 free minutes a month), nothing passes through a server of ours, and turning it off removes the secrets and the workflow. Your PC keeps its desktop and voice alerts and leaves phone and email to the cloud, so nothing arrives twice. The Cloud page walks through every screen." },
  { q: "How do I uninstall?", a: "Windows Settings → Apps → Assignment Monitor → Uninstall. It closes the app, removes the background tasks and the Startup entry, offers to turn off cloud checks if they are on, deletes the program, and asks whether to delete your saved sign-in and cached data too." },
  { q: "Installer or portable zip?", a: "The installer is the easy path: Start Menu and Desktop icons, in-app updates, clean uninstall. The zip is the same program without an installer; unzip it anywhere and run AssignmentMonitor.exe. Both keep their data in your local app-data folder." },
  { q: "Where is my data kept?", a: "In %LOCALAPPDATA%\\Assignment Monitor: your encrypted sign-in and channel keys, preferences, the cached assignments, attendance, exam plan, announcements, file lists and timetable, a log and the browser profile. The optional calendar file lives in Documents. Nothing is stored anywhere else." },
  { q: "Can I run it from source?", a: "Yes. Clone the repository, install the pinned requirements and run python app.py. The README has the exact steps, and python build.py produces the same installer the releases ship." },
];

export const WHAT_INSTALLER_DOES = [
  ["Installs for your user", "Into your local Programs folder. No administrator password, nothing touches other accounts."],
  ["Adds shortcuts", "A Start Menu entry and, if you leave the box ticked, a Desktop icon."],
  ["Opens the app", "First run is the sign-in screen: enrollment number, CMS password, campus."],
  ["Creates the background tasks", "Only when you tick \"Check automatically\": a 7 PM check, a catch-up after sign-in and the hourly due-day reminder, all under your own account."],
];

export const UNINSTALL_STEPS = [
  "Closes the window and any background check that is running.",
  "Unregisters the three scheduled tasks and removes the Startup entry.",
  "Deletes the program folder, the shortcuts and the Apps & features entry.",
  "Asks whether to also delete your saved sign-in, settings and cached data. Yes leaves nothing behind; No keeps your account for a reinstall.",
  "If cloud checks are on, asks whether to turn them off too, removing your login and the workflow from your GitHub repository.",
];
