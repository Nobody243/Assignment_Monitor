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
  { spot: [21.9, 10.5, 75.8, 27.1], label: "Today at a glance", title: "What is next, and how you stand", text: "A greeting with the next deadline counting down, your submitted share, attendance, CGPA, what is due this week and what is overdue. Nothing to open first." },
  { spot: [21.9, 39.6, 47.7, 29.8], label: "This week", title: "Your week: classes and deadlines on one grid", text: "The CMS timetable with every deadline pinned to its day, so a quiet Tuesday and a crowded Thursday are obvious before they arrive." },
  { spot: [70.9, 39.5, 26.6, 29.3], label: "Due today", title: "The urgent one, with Upload right there", text: "Whatever is due soonest and still unsubmitted gets a big card with the time left. Press Upload, choose the file, confirm: the app uses the portal's own form and checks it worked." },
  { spot: [70.9, 71, 26.6, 29], label: "Needs attention", title: "Only the things that need you", text: "Due today, overdue work, a course under the 75% attendance rule and how many classes will fix it. When all is well this list is empty." },
  { spot: [21.9, 71.5, 47.7, 22.5], label: "Deadline load", title: "See a crowded fortnight before you are in it", text: "A bar for each of the next 14 days. Stacked deadlines stand out, so you can start the heavy week early." },
  { spot: [1.2, 2.5, 17.6, 95], label: "Always a click away", title: "Four colour palettes, light or dark, tray or window", text: "Switch the look in Settings. Close the window and the app keeps running in the tray; the background checks run even when it is closed." },
];

export const FEATURES = [
  { n: "01", tag: "Deadlines", title: "Catches extended deadlines", text: "When a teacher moves a date, the LMS squashes old and new into one string. The app reads both and flags the change.", datestr: { now: "4 October 2026 - 11:50 am", was: "13 September 2026-11:55 am" } },
  { n: "02", tag: "Reminders", title: "Reminds you out loud", text: "On the day something is due and still unsubmitted, a spoken reminder and a Windows notification every hour until it's done. Pick the voice, volume and speed." },
  { n: "03", tag: "Attendance", title: "Knows your attendance margin", text: "Every course's hours and percentage from the CMS, how many classes you can still miss for the 75% rule, and a notification the day an absence is recorded.", list: [["Under minimum", "needs 10 h present"], ["At risk", "can miss 1 h"], ["On track", "can miss 6 h"]] },
  { n: "04", tag: "Exams", title: "Carries your seating plan", text: "Date, session, time, room, row and seat for every paper, a countdown on the dashboard, and a notification the day before and on the morning of the exam." },
  { n: "04b", tag: "Results", title: "Keeps your transcript and GPA", text: "Every semester's grades from the CMS with the GPA and CGPA worked out the way the portal does, a notification the moment a result is posted, and a what-if calculator: pick the grades you expect and see where the CGPA lands, or the semester GPA a target needs." },
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
  { n: "14", tag: "Cloud", title: "Checks with the PC off", text: "Optional. One GitHub sign-in and the same check runs each morning and evening (07:43 and 18:37) on GitHub's machines, from a private repository in your own account, and alerts your phone and inbox. Free, no server of ours, off until you turn it on. Walkthrough on the Cloud page.", list: [["Where", "your GitHub account"], ["When", "07:43 and 18:37"], ["Cost", "free"]] },
];

export const STEPS = [
  { title: "Install", text: "Run the setup. It installs for your user account only, no administrator password, and adds a Start Menu and Desktop icon." },
  { title: "Sign in once", text: "Enrollment number, CMS password, campus. The app verifies the sign-in live and reads every course of the semester." },
  { title: "Let it run", text: "Leave \"Check automatically\" ticked. From then on it checks at 7 PM, after you sign in to Windows, and hourly on due days." },
];

export const SHOT_V = "182";
export const shot = (id, theme) => `/assets/shot-${id}-${theme}.png?v=${SHOT_V}`;

export const SCREENS = [
  { id: "dashboard", label: "Home", caption: "Home: the next deadline with a countdown, your week, what needs attention, the deadline load and your standing." },
  { id: "assignments", label: "Assignments", caption: "Assignments: to do, overdue and submitted at a glance, extension history, marks, files, and Upload, Replace or Delete when the portal allows it." },
  { id: "attendance", label: "Attendance", caption: "Attendance: every course's hours, the margin to the 75% rule, and the class-by-class record." },
  { id: "exams", label: "Exams", caption: "Exams: the seating plan with room, row and seat, and a countdown to each paper." },
  { id: "results", label: "Results", caption: "Results: every semester's grades, GPA and CGPA, and the calculator: pick the grades you expect, set a target CGPA, try other grades in a past semester." },
  { id: "timetable", label: "Timetable", caption: "Timetable: the week as a clean grid, a colour per course, today and the current time marked; save it as PNG, JPG or PDF." },
  { id: "lectures", label: "Lectures", caption: "Lectures: every course's notes by week; tick files and download them into course / week folders." },
  { id: "announcements", label: "Announcements", caption: "Announcements: every course's notices in one feed, newest first." },
  { id: "settings", label: "Settings", caption: "Settings: profile, appearance, notifications, tracking, background and cloud checks, data and files, activity and updates." },
];

export const PRIVACY_CARDS = [
  { tag: "Encrypted by Windows", title: "DPAPI, your account only", text: "The portal password is protected with Windows Data Protection for your user account. Another user or another PC cannot read it, and it is never written to the log." },
  { tag: "Two hosts, HTTPS", title: "Talks only to the portal", text: "The only connections are to cms.bahria.edu.pk and lms.bahria.edu.pk, plus an optional, switchable check of GitHub for new versions. Phone and email alerts, if you turn them on, go from your PC to your own mailbox and your phone's browser; this site runs no server and keeps no accounts. No analytics, no telemetry." },
  { tag: "Read the code", title: "Open source, built in public", text: "MIT licensed. Releases are built by GitHub Actions straight from the repository, and you can build the same thing yourself with one command." },
  { tag: "Optional cloud", title: "Your account, not ours", text: "Cloud checks, if you turn them on, keep your login as encrypted secrets in a private repository in your own GitHub account and run there. The app tells you exactly what goes where before you agree, and turning it off removes it." },
];

export { FAQ } from "./faq.js";

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
