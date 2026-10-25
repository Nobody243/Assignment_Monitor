/* Short guides for Bahria students, written for the questions they actually type into a search box. Plain data,
   no imports, so scripts/prerender.mjs can read it in Node and write each guide as a static page. Keep every
   claim about the portal to what the app itself reads; the university's own rules are stated as "confirm with
   your department", never as a promise. */

export const GUIDES = {
  "bahria-attendance": {
    title: "Bahria University attendance: how the 75% rule works, in hours",
    short: "The 75% attendance rule",
    kicker: "Guide · Attendance",
    description: "How Bahria University counts attendance per course and in hours, what 75% means for a 3-hour lab, how to work out how many classes you can still miss, and where the CMS shows it.",
    lede: "Attendance on the CMS is counted per course and in hours, not in classes. That is why a missed lab hurts three times as much as a missed lecture, and why the percentage can drop faster than you expect.",
    updated: "2026-10-25",
    sections: [
      {
        h: "What the rule says",
        p: [
          "Bahria University applies a minimum attendance requirement, usually 75% per course, to sit the final examination. The exact threshold and any exceptions (medical leave, university duty) are set by your department, so confirm the number there. Everything below assumes 75%.",
          "The percentage is simple: hours you were marked present divided by hours of class held so far. It is calculated course by course. Being at 95% in one subject does nothing for the one at 70%.",
        ],
      },
      {
        h: "Why hours, not classes",
        p: [
          "A one-hour lecture and a three-hour lab are both one class on your timetable, but the CMS records them as one hour and three hours. Miss the lab and your percentage falls three times as far.",
          "That is also why lab courses, which meet once a week, are the ones most often in the red. Three hours missed out of a 30-hour course is already 10% gone.",
        ],
      },
      {
        h: "Working out your margin",
        p: ["Two numbers matter: the hours held so far and the hours you were present. Three examples with a 30-hour course so far:"],
        list: [
          ["24 present of 30 (80%)", "You can miss 2 more hours. At 24 of 32 you are exactly on 75%; one more hour missed and you are under."],
          ["21 present of 30 (70%)", "You are under. You need 6 straight hours present with no miss to climb back to 75% (27 of 36)."],
          ["30 present of 30 (100%)", "You could miss 10 hours and still sit at 75% (30 of 40). Do not plan on it; some weeks hold more class than others."],
        ],
        after: "The arithmetic for \"how many can I still miss\" is present ÷ 0.75 − held. For \"how many do I need\" it is (0.75 × held − present) ÷ 0.25, rounded up. The app does this for every course after each check and shows the weakest first.",
      },
      {
        h: "Where to see it on the CMS",
        p: [
          "Sign in to cms.bahria.edu.pk and open the attendance page. Each course lists hours held, hours present and the percentage, with a detail link that shows every class with its date and whether you were marked present or absent.",
          "Absences are entered by the teacher, sometimes days after the class. Checking once at the start of the semester tells you nothing; the number that matters is the one in the last two weeks before exams.",
        ],
      },
      {
        h: "What to do when you are short",
        list: [
          ["Count the remaining hours", "Look at the timetable: how many hours of that course are left in the semester? If the hours you need are more than the hours left, talk to the department now, not in the exam week."],
          ["Check for mistakes", "A class you attended but were marked absent for can usually be corrected by the teacher if you ask within a few days. The detail page tells you the date."],
          ["Protect the labs", "A lab is worth three lectures. If you have to miss something, do not make it the lab."],
        ],
      },
      {
        h: "How Assignment Monitor helps",
        p: [
          "After every check the app reads the attendance page for all your courses and shows each one as hours, percentage and margin: how many hours you can still miss, or how many you need to be present for. Courses under the minimum are red on the dashboard, weakest first.",
          "The day a new absence is recorded you get a Windows notification, and on your phone or by email if you have linked them. The minimum is 75% by default and can be changed in Settings to match your department's rule.",
        ],
      },
    ],
    related: [["/guide/bahria-lms-deadlines", "LMS deadlines, and how extensions show up"], ["/download", "Download the app"], ["/faq", "FAQ"]],
  },

  "bahria-lms-deadlines": {
    title: "Bahria LMS deadlines: how due dates and extensions work, and how not to miss one",
    short: "LMS deadlines and extensions",
    kicker: "Guide · Deadlines",
    description: "Where Bahria LMS shows assignment due dates, how an extended deadline appears, why announcements matter, what happens to late submissions, and a routine that catches every deadline across all your courses.",
    lede: "The LMS keeps every deadline on a different page: one assignments list per course, one announcements page per course. With eight or nine courses that is up to eighteen pages to check, which is exactly how a deadline slips past.",
    updated: "2026-10-25",
    sections: [
      {
        h: "Where the due date lives",
        p: [
          "Sign in to lms.bahria.edu.pk, pick the semester and a course, and open Assignments. Each row has the title, the date it was posted, the due date and time, your submission status, and the files: the teacher's brief, your own upload once you have submitted, and later any returned or solution file.",
          "The due time is part of the deadline. A date shown as 20 October, 08:00 am closes in the morning, not at midnight. Plenty of submissions are lost to that assumption.",
        ],
      },
      {
        h: "How an extension appears",
        p: [
          "When a teacher moves a deadline, the LMS does not add a new row. The due-date cell changes, and in many courses it now shows both the old and the new date run together, so a quick glance reads the wrong one.",
          "The extension is often announced first, and sometimes only, on the course's Announcements page. If you only look at the assignments list you can miss both the extension and the reason for it.",
        ],
      },
      {
        h: "Submissions, returns and solutions",
        list: [
          ["Your upload", "After you submit, your own file appears in the row. Download a copy and keep it; students who lose their PC or clear a folder often need the submitted version again."],
          ["Returned work", "If the teacher returns your file with marks or comments, a returned file appears in the same row. Nothing announces it; you have to look."],
          ["Solution", "Some teachers post a solution file after the deadline. Same row, same silence."],
          ["Late work", "Whether the LMS accepts a late upload, and whether it is marked, is the teacher's setting. Do not count on it."],
        ],
      },
      {
        h: "A routine that works",
        list: [
          ["Once a day, one pass", "Open every course's Assignments and Announcements once a day. Evening is best; teachers post after classes. Write the due date and time somewhere you will see it."],
          ["Treat the time as the deadline", "Plan to submit the evening before an 08:00 deadline. The LMS has no grace period you can rely on."],
          ["Save what you submit", "Download your own submission after uploading it. The LMS link to it does not last forever."],
          ["Re-read dates that look odd", "A due-date cell with two dates in it means an extension. Take the later one, and check Announcements for the conditions."],
        ],
      },
      {
        h: "How Assignment Monitor helps",
        p: [
          "The app signs in with your own account and reads every course's assignments and announcements in one pass, every evening and whenever you sign in to Windows. New assignments, changed due dates and new announcements each produce a notification; a deadline that moved is flagged as extended, with the old and the new date.",
          "On the day something is due and still unsubmitted, it reminds you out loud every hour until you submit. Alerts can also reach your phone and your inbox, and with cloud checks on they keep coming while the PC is off. Each assignment row offers the brief, your submission, returned work and the solution for download in one click.",
        ],
      },
    ],
    related: [["/guide/bahria-attendance", "The 75% attendance rule, in hours"], ["/download", "Download the app"], ["/cloud", "Cloud checks"]],
  },
};

export const GUIDE_SLUGS = Object.keys(GUIDES);
