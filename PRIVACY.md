# Privacy and terms

**Assignment Monitor is an independent, open-source student project. It is not affiliated with, endorsed by, or supported by Bahria University.**

## What it does

With your permission, the app signs in to the Bahria University CMS/LMS portal using the enrollment number and password you provide, and reads your own pages, the same way you would in a browser: the LMS assignments, announcements, lecture-notes and Miscellaneous-files lists for each course, and the CMS attendance, attendance detail, exam seating plan and timetable. Each of these can be switched off in Settings. Files (lecture notes, an assignment's brief, your own submission, returned work, a posted solution) are downloaded only when you click Download for them, into a folder on your PC that you choose. It does this on your PC, on a schedule you control, and stores the results on your PC only.

## What it does not do

- It does not send your credentials or your data to the author or to any third party. The optional phone and email channels deliver alerts only to your own mailbox and your own phone (see below).
- It does not access anyone else's account or data.
- It does not change anything on the portal: it never submits, uploads, or posts.
- It does not collect analytics, crash reports, or usage statistics.
- The optional update check contacts GitHub (`api.github.com`) to read the latest release number; you can turn it off in Settings.

## Your responsibilities

- Use it only with your own account.
- Keep your PC secure: anyone who can sign in to your Windows account can open the app.
- The university's own terms of use apply to your portal account. If the university asks you not to use automated tools with your account, stop using the app.

## Deleting your data

Uninstalling closes the app, removes the background tasks and the program, and asks whether to delete your saved sign-in, settings, channel keys and cached data (assignments, attendance, exam plan, announcements, lecture and file lists, timetable). Say yes and nothing remains in `%LOCALAPPDATA%\Assignment Monitor`; otherwise delete that folder yourself. Files you chose to download and the optional calendar file live in `Documents\Assignment Monitor` and are yours to keep or delete. A paired phone keeps its notification permission for the website until you remove it in the phone's browser settings; without the keys on your PC it can never receive another push. If cloud checks are on, the uninstaller offers to turn them off as well (removing your login and the workflow from your GitHub repository); say yes unless you mean to keep them running without the app.

## Warranty

The app is provided "as is" under the MIT license, without warranty of any kind. Deadlines shown by the app come from the portal and can be wrong or out of date; always confirm on the LMS itself.

## Phone, email and calendar (optional, off by default)

- **Email** is sent from your own mailbox to your own address, over TLS, using an app password that is stored encrypted with Windows DPAPI like the portal password. No third party receives the mail.
- **Phone pushes** use the Web Push standard. The signing keys are generated on your PC. When you pair a phone, the page on assignment-monitor.vercel.app hands your PC the phone's push address once, encrypted with a key that only the QR code carried, through a single-use topic on a public ntfy relay (ntfy.sh, or one of three other public instances when that one is rate-limiting the phone's network); the relay sees only ciphertext and the topic is never used again. After that, alerts travel from your PC to the phone's browser push service (Google's, Apple's or Mozilla's, depending on the browser), encrypted end to end as the standard requires. The website has no accounts and no database and cannot see who paired or what is sent.
- **Calendar** writes an .ics file in Documents › Assignment Monitor on your PC. If you also enable invites, they go out by the email channel above.

## Cloud checks (optional, off by default)

Everything above happens on your PC, so a PC that is switched off checks nothing. Cloud checks move the same check to GitHub's machines, inside your own GitHub account, and change the privacy picture in one way, which the app spells out before you agree:

- The app creates a **private repository** (`assignment-monitor-cloud`) in your GitHub account and stores your enrollment number, portal password and the phone and email keys there as **GitHub Actions secrets**. GitHub encrypts them at rest; the app encrypts them with the repository's public key before they leave your PC; they are readable only by the check while it runs and are masked in its logs. Your password therefore lives in two places: encrypted on your PC and encrypted at GitHub.
- The repository also holds the **cache** of what was last seen (assignments, attendance, exams, announcements, lecture list, timetable), the same files your PC keeps, so the cloud can tell what is new. It is private to your account.
- GitHub's machines sign in to the portal twice a day (8 AM and 7 PM Pakistan time) and send the alerts to your phone and mailbox through the channels above. While cloud checks are on, your PC keeps its desktop and voice alerts and leaves phone and email to the cloud, so nothing arrives twice.
- The app signs in to GitHub with GitHub's device flow and keeps the resulting token encrypted on your PC like the other secrets. GitHub grants it the `repo` and `workflow` permissions, which cover every repository in your account; the app touches only the one above. You can revoke the grant at any time at github.com/settings/applications.
- Nothing passes through a server of ours: your PC talks to api.github.com, and GitHub's machines talk to the portal and to your channels. GitHub's own terms and privacy policy apply to what is stored there.

Turning cloud checks off removes the secrets and the workflow from the repository and the token from your PC; the empty repository is yours to delete on GitHub (the app opens the page for you).
