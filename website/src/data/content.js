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
  "Checks every evening at 19:00", "Catch-up check after you sign in", "Hourly voice reminder on due days", "Catches extended deadlines",
  "Attendance margin per course", "Exam room and seat, with a countdown", "Course announcements in one feed", "Lecture notes, downloaded into tidy folders", "Runs in the tray, no window needed",
  "Islamabad · Lahore · Karachi campuses", "Nothing sent anywhere but the portal",
];

export const NUMBERS = [
  { value: 19, suffix: ":00", text: "Automatic check every evening, plus a catch-up when you sign in" },
  { value: 60, suffix: " min", text: "Between voice reminders while an unsubmitted assignment is due today" },
  { value: 5, suffix: " things", text: "Watched for you: assignments, attendance, the exam seating plan, announcements and lecture notes" },
  { value: 3, suffix: " campuses", text: "Islamabad, Lahore and Karachi. Pick yours at sign-in; nothing of yours leaves your PC" },
];

export const TOUR = [
  { spot: [28.2, 20.5, 59.7, 14.8], label: "Next deadline", title: "The next deadline, with a countdown", text: "Whatever is due soonest and still unsubmitted sits at the top, coloured by urgency. Today is red, this week is amber, later is quiet." },
  { spot: [28.2, 36.4, 59.8, 10.6], label: "Six counters", title: "Pending, due today, this week, extended, overdue, submitted", text: "Each counter is a filter. Click it and the Assignments page opens on exactly that slice." },
  { spot: [28.2, 48.2, 35.0, 37.9], label: "Attendance", title: "Your attendance margin, weakest course first", text: "Every course's percentage from the CMS. Red is under the 75% rule; the Attendance page behind it says how many classes you can still miss, or must attend." },
  { spot: [64.1, 48.2, 23.9, 37.9], label: "Next exam", title: "Room and seat before you have to ask", text: "The seating plan from the CMS with a countdown, time, room, row and seat. A notification comes the day before and on the morning of the paper." },
  { spot: [1, 2.5, 16, 96], label: "Always a click away", title: "Light or dark, tray or window", text: "Switch the theme any time. Close the window and it keeps running in the tray; the background checks run even when it doesn't." },
];

export const FEATURES = [
  { n: "01", tag: "Deadlines", title: "Catches extended deadlines", text: "When a teacher moves a date, the LMS squashes old and new into one string. The app reads both and flags the change.", datestr: { now: "4 October 2026 - 11:50 am", was: "13 September 2026-11:55 am" } },
  { n: "02", tag: "Reminders", title: "Reminds you out loud", text: "On the day something is due and still unsubmitted, a spoken reminder and a Windows notification every hour until it's done. Pick the voice, volume and speed." },
  { n: "03", tag: "Attendance", title: "Knows your attendance margin", text: "Every course's hours and percentage from the CMS, how many classes you can still miss for the 75% rule, and a notification the day an absence is recorded.", list: [["Under minimum", "needs 10 h present"], ["At risk", "can miss 1 h"], ["On track", "can miss 6 h"]] },
  { n: "04", tag: "Exams", title: "Carries your seating plan", text: "Date, session, time, room, row and seat for every paper, a countdown on the dashboard, and a notification the day before and on the morning of the exam." },
  { n: "05", tag: "Announcements", title: "Reads every course's notices", text: "Announcements from all your course pages in one feed, newest first, with a notification for each new one. Deadline extensions are often posted here first." },
  { n: "06", tag: "Lectures", title: "Collects your lecture notes", text: "Every course's notes in one list by week. Tick the files you want and they download through the app's own sign-in into course / week folders; what you already have is skipped." },
  { n: "07", tag: "Automation", title: "Runs itself", text: "Three Windows tasks under your own account. No admin rights, no service, and they work with the window closed.", list: [["Daily check", "19:00"], ["Catch-up check", "2 min after sign-in"], ["Due-today reminder", "hourly"]] },
  { n: "08", tag: "Tray", title: "Lives in the tray", text: "Close the window and it keeps running quietly. Right-click the icon to open, sync now, or quit. Optionally starts with Windows." },
  { n: "09", tag: "Updates", title: "Updates itself, safely", text: "Checks the project's GitHub releases on start (switchable). One click downloads the new installer, closes, reinstalls and reopens. Your sign-in and data are kept." },
  { n: "10", tag: "Source", title: "Open, auditable, yours", text: "MIT licensed. Every release is built by GitHub Actions from the public repository, with tests and a dependency audit on every commit." },
];

export const STEPS = [
  { title: "Install", text: "Run the setup. It installs for your user account only, no administrator password, and adds a Start Menu and Desktop icon." },
  { title: "Sign in once", text: "Enrollment number, CMS password, campus. The app verifies the sign-in live and reads every course of the semester." },
  { title: "Let it run", text: "Leave \"Check automatically\" ticked. From then on it checks at 7 PM, after you sign in to Windows, and hourly on due days." },
];

export const SHOT_V = "134";
export const shot = (id, theme) => `/assets/shot-${id}-${theme}.png?v=${SHOT_V}`;

export const SCREENS = [
  { id: "dashboard", label: "Dashboard", caption: "Dashboard: next deadline, counters, attention list, course progress." },
  { id: "attendance", label: "Attendance", caption: "Attendance: every course's hours, the margin to the 75% rule, and the class-by-class record." },
  { id: "exams", label: "Exams", caption: "Exams: the seating plan with room, row and seat, and a countdown to each paper." },
  { id: "lectures", label: "Lectures", caption: "Lectures: every course's notes by week; tick files and download them into course / week folders." },
  { id: "announcements", label: "Announcements", caption: "Announcements: every course's notices in one feed, newest first." },
  { id: "assignments", label: "Assignments", caption: "Assignments: filters, course picker, search, extension history and marks." },
  { id: "settings", label: "Settings", caption: "Settings: account, theme, tray, voice and notifications, campus tracking, automatic checks, privacy." },
  { id: "setup", label: "Sign-in", caption: "First run: sign in once, tick automatic checks, done." },
];

export const PRIVACY_CARDS = [
  { tag: "Encrypted by Windows", title: "DPAPI, your account only", text: "The portal password is protected with Windows Data Protection for your user account. Another user or another PC cannot read it, and it is never written to the log." },
  { tag: "Two hosts, HTTPS", title: "Talks only to the portal", text: "The only connections are to cms.bahria.edu.pk and lms.bahria.edu.pk, plus an optional, switchable check of GitHub for new versions. No analytics, no telemetry." },
  { tag: "Read the code", title: "Open source, built in public", text: "MIT licensed. Releases are built by GitHub Actions straight from the repository, and you can build the same thing yourself with one command." },
];

export const FAQ = [
  { q: "Windows says \"Windows protected your PC\". Is it safe?", a: "Yes. The warning appears because the installer is not yet code-signed; the project is applying for a free open-source certificate. Click \"More info\", then \"Run anyway\". If you prefer, build it yourself from the source code with one command; the result is identical." },
  { q: "Is this an official Bahria University app?", a: "No. Assignment Monitor is an independent student project. It is not affiliated with, endorsed by, or supported by Bahria University." },
  { q: "What does it do with my account?", a: "It signs in with your own credentials and reads your own pages, the same way you would in a browser: the LMS assignments, announcements and lecture-notes lists, and the CMS attendance and exam seating plan. Each can be switched off in Settings. Lecture files are downloaded only when you tick them and click Download, to a folder you choose. It never submits, uploads or changes anything on the portal, and it never sends your data anywhere." },
  { q: "Do I need Google Chrome?", a: "If Chrome is installed it is used in the background. If not, a browser engine is downloaded once automatically. You never see a browser window." },
  { q: "Which alerts are spoken?", a: "Only assignment reminders use the voice: the due-today reminder and the after-sync summary. Attendance, exam and announcement alerts are ordinary Windows notifications, and every category can be switched off in Settings." },
  { q: "Does my PC need to be on at 7 PM?", a: "For the 7 PM check, yes, but if it was off a catch-up check runs two minutes after you next sign in to Windows. The hourly reminder only fires while something is due that day." },
  { q: "How do I uninstall?", a: "Windows Settings → Apps → Assignment Monitor → Uninstall. It closes the app, removes the background tasks and the Startup entry, deletes the program, and asks whether to delete your saved sign-in and cached data too." },
  { q: "Installer or portable zip?", a: "The installer is the easy path: Start Menu and Desktop icons, in-app updates, clean uninstall. The zip is the same program without an installer; unzip it anywhere and run AssignmentMonitor.exe. Both keep their data in your local app-data folder." },
  { q: "Where is my data kept?", a: "In %LOCALAPPDATA%\\Assignment Monitor: your encrypted sign-in, preferences, the cached assignments, attendance, exam plan and announcements, a log and the browser profile. Nothing is stored anywhere else." },
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
];
