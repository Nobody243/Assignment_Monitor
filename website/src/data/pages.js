/* One place for every page's title, description and a plain-text outline of what it says.

   The React pages read their title and description from here (usePageMeta(...metaFor(path))), and
   scripts/prerender.mjs reads the same data after `vite build` to write one static HTML file per route: the
   right <title>, description, canonical and social tags in the head, and the outline inside #root beneath the
   boot cover, so crawlers that do not run scripts (and link previews) still see the page's own words. React
   replaces the outline the moment it mounts.

   No imports: this file must load in plain Node. */
import { GUIDES } from "./guides.js";

export const SITE = "https://assignment-monitor.saaddev.top";
export const BASE = "Assignment Monitor";
export const DEFAULT_TITLE = `${BASE} — never miss a Bahria LMS deadline`;

export const PAGES = {
  "/": {
    title: "",
    description: "A free, open-source Windows app that watches your Bahria University LMS and CMS: assignments with extended-deadline detection, attendance margins, the exam seating plan and course announcements. Everything stays on your PC.",
    h1: "Never miss a Bahria LMS deadline again.",
    lede: "Assignment Monitor is a free, open-source Windows app for Bahria University students. It signs in to the LMS and CMS with your own account, reads every course, and tells you the moment something changes: out loud, on your phone, or by email. Your password never leaves your PC.",
    sections: [
      { h: "What it watches", bullets: [
        "Assignments across every course, with the due date and time, your submission status, and extended deadlines flagged with the old and the new date.",
        "Attendance per course in hours and percent, with how many hours you can still miss for the 75% rule, or how many you need.",
        "The exam seating plan: date, time, room, row and seat, with a countdown and a reminder the day before.",
        "Course announcements from every course in one feed.",
        "Lecture notes and course files, downloaded into tidy course and week folders.",
        "The timetable, drawn as a clean week grid and saved as PNG, JPG or PDF.",
      ] },
      { h: "How it tells you", bullets: [
        "Windows notifications for every change; a spoken reminder every hour on the day an assignment is due and still unsubmitted.",
        "Phone alerts without an app: pair a phone by scanning a code.",
        "Email from your own mailbox, and calendar invites if you want them.",
        "Cloud checks: the same check twice a day on GitHub's machines from a private repository in your own account, so alerts arrive with the PC off.",
      ] },
      { h: "Three steps", bullets: [
        "Install: a normal Windows setup for your user account, no administrator password.",
        "Sign in once: enrollment number, CMS password, campus. The app verifies the sign-in live.",
        "Let it run: it checks every evening, after you sign in to Windows, and hourly on due days.",
      ] },
      { h: "Privacy", p: [
        "No server, no account, no analytics. The portal password is encrypted with Windows DPAPI for your user account. The only connections are to cms.bahria.edu.pk and lms.bahria.edu.pk, plus an optional check of GitHub for new versions. MIT licensed; every release is built by GitHub Actions from the public repository.",
        "Assignment Monitor is an independent student project. It is not affiliated with, endorsed by, or supported by Bahria University.",
      ] },
    ],
  },
  "/download": {
    title: "Download",
    description: "Download Assignment Monitor for Windows: installer or portable zip, what the installer does, SmartScreen, requirements and uninstall.",
    h1: "Get Assignment Monitor for Windows.",
    lede: "Windows 10 or 11, 64-bit. No administrator rights, no account. Two ways to get it, both built by GitHub Actions from the public source.",
    sections: [
      { h: "Installer", p: ["The easy path: Start Menu and Desktop icons, in-app updates and a clean uninstall. Installs for your user account only."] },
      { h: "Portable zip", p: ["The same program without an installer. Unzip it anywhere and run AssignmentMonitor.exe. Data lives in your local app-data folder either way."] },
      { h: "Windows may say \"protected your PC\"", p: ["The installer is not yet code-signed (the project is applying for a free open-source certificate), so SmartScreen warns the first time. Click \"More info\", then \"Run anyway\". Or clone the repository and build the same installer yourself."] },
      { h: "Uninstall", p: ["Settings → Apps → Assignment Monitor → Uninstall. It closes the app, removes the background tasks and the Startup entry, offers to turn off cloud checks, deletes the program, and asks whether to delete your saved sign-in and cached data too."] },
    ],
  },
  "/cloud": {
    title: "Cloud checks",
    description: "How Assignment Monitor's cloud checks work: the same check on GitHub's machines from a private repository in your own account, so phone and email alerts arrive with the PC off. Every step with screenshots.",
    h1: "Alerts with the PC off.",
    lede: "Optional, free, and in your own GitHub account: the same check the PC runs, done twice a day on GitHub's machines, so your phone and mailbox hear about a new deadline whether your laptop is open or in a bag. Off until you turn it on.",
    sections: [
      { h: "Setting it up", bullets: [
        "Settings → Cloud checks → Set up. The section says what will happen and who does what.",
        "Read what goes where, then continue: a private repository in your own GitHub account, your login and channel keys stored there as encrypted secrets.",
        "Sign in with a one-time code: press Open GitHub, paste the code, press Authorize. No password is typed into the app.",
        "Done. A first check runs at once and a test alert reaches your phone and mailbox. From then on it runs at 07:43 and 18:37 Pakistan time.",
        "Afterwards, Settings shows the last run and its result, with Run now and Open on GitHub beside it. Turning it off removes the secrets and the workflow.",
      ] },
      { h: "What it costs", p: ["Nothing. A check uses a few of GitHub's 2,000 free Actions minutes a month. Nothing passes through a server of ours; there is none."] },
    ],
  },
  "/privacy": {
    title: "Privacy & security",
    description: "What Assignment Monitor stores, where, how it is protected, and the only hosts it talks to.",
    h1: "No server. No account. Nothing leaves your PC.",
    lede: "Assignment Monitor is an independent, open-source student project. It is not affiliated with, endorsed by, or supported by Bahria University. Here is exactly what it keeps and who it talks to.",
    sections: [
      { h: "What it stores", p: ["Everything lives in one folder on your PC (%LOCALAPPDATA%\\Assignment Monitor): the portal password, mail app password and phone push keys encrypted with Windows DPAPI for your user account; your enrollment number, campus and preferences; the cached assignments, attendance, exam plan, announcements, lecture list, timetable and log; and the browser profile. With cloud checks on, the same login and keys are kept as encrypted secrets in a private repository in your own GitHub account."] },
      { h: "Who it talks to", bullets: [
        "The portal: cms.bahria.edu.pk and lms.bahria.edu.pk over HTTPS, to sign in and read your own pages. It only ever reads.",
        "Your channels, only if you turn them on: your own mail server over TLS and your phone's browser push service.",
        "GitHub: the optional update check, and your private repository if cloud checks are on.",
        "A browser engine, downloaded once from Microsoft's Playwright CDN only if Google Chrome is not installed.",
      ] },
      { h: "What it does not do", bullets: [
        "It does not send your credentials or your data to the author or to any third party.",
        "It does not access anyone else's account or data.",
        "It does not change anything on the portal: it never submits, uploads or posts.",
        "It does not collect analytics, crash reports or usage statistics.",
      ] },
    ],
  },
  "/faq": {
    title: "FAQ",
    description: "Answers about SmartScreen, accounts, Chrome, schedules, phone and email alerts, cloud checks, uninstalling and running Assignment Monitor from source.",
    h1: "Questions, answered.",
    lede: "Short answers. For anything else, open an issue on GitHub and include the app version from Settings → About.",
    sections: [],      // the prerender appends the FAQ itself (src/data/faq.js) and its FAQPage structured data
  },
  "/phone": {
    title: "Phone alerts",
    description: "Pair your phone with Assignment Monitor on your PC so alerts arrive as notifications here.",
    h1: "Alerts, on your phone.",
    lede: "Assignment Monitor on your PC can push its alerts here: deadlines, attendance, exam seats, announcements, new notes. No app to install, no account, nothing stored anywhere but this phone and your PC.",
    sections: [
      { h: "How it stays private", bullets: [
        "The push keys are made on your PC. Alerts travel from your PC to the phone's push service, encrypted so even that service cannot read them.",
        "This page hands your PC a one-time address for the phone, encrypted with a key that only the QR code carried, through a throw-away relay topic that is never used again.",
        "The website has no accounts and no database; it cannot see who paired or what is sent.",
      ] },
    ],
  },
};

for (const [slug, g] of Object.entries(GUIDES)) {
  PAGES[`/guide/${slug}`] = {
    title: g.short,
    description: g.description,
    h1: g.title,
    lede: g.lede,
    guide: slug,
    sections: g.sections.map((s) => ({ h: s.h, p: s.p, bullets: s.list ? s.list.map(([b, t]) => `${b}: ${t}`) : undefined, after: s.after })),
  };
}

/* [title, description] for usePageMeta. */
export function metaFor(path) {
  const p = PAGES[path];
  return [p.title, p.description];
}

export const ROUTES = Object.keys(PAGES);
