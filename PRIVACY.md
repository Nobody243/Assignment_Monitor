# Privacy and terms

**Assignment Monitor is an independent, open-source student project. It is not affiliated with, endorsed by, or supported by Bahria University.**

## What it does

With your permission, the app signs in to the Bahria University CMS/LMS portal using the enrollment number and password you provide, and reads your own pages, the same way you would in a browser: the LMS assignments, announcements, lecture-notes and Miscellaneous-files lists for each course, and the CMS attendance, attendance detail, exam seating plan and timetable. Each of these can be switched off in Settings. Lecture files themselves are downloaded only when you select them and click Download, into a folder on your PC that you choose. It does this on your PC, on a schedule you control, and stores the results on your PC only.

## What it does not do

- It does not send your credentials or your data to the author or to any third party.
- It does not access anyone else's account or data.
- It does not change anything on the portal: it never submits, uploads, or posts.
- It does not collect analytics, crash reports, or usage statistics.
- The optional update check contacts GitHub (`api.github.com`) to read the latest release number; you can turn it off in Settings.

## Your responsibilities

- Use it only with your own account.
- Keep your PC secure: anyone who can sign in to your Windows account can open the app.
- The university's own terms of use apply to your portal account. If the university asks you not to use automated tools with your account, stop using the app.

## Deleting your data

Uninstalling closes the app, removes the background tasks and the program, and asks whether to delete your saved sign-in, settings and cached data (assignments, attendance, exam plan, announcements). Say yes and nothing remains; otherwise delete the folder `%LOCALAPPDATA%\Assignment Monitor` yourself.

## Warranty

The app is provided "as is" under the MIT license, without warranty of any kind. Deadlines shown by the app come from the portal and can be wrong or out of date; always confirm on the LMS itself.

## Phone, email and calendar (optional, off by default)

- **Email** is sent from your own mailbox to your own address, over TLS, using an app password that is stored encrypted with Windows DPAPI like the portal password. No third party receives the mail.
- **Phone pushes** use the Web Push standard. The signing keys are generated on your PC. When you pair a phone, the page on assignment-monitor.vercel.app hands your PC the phone's push address once, encrypted with a key that only the QR code carried, through a single-use topic on the public relay ntfy.sh; the relay sees only ciphertext and the topic is never used again. After that, alerts travel from your PC to the phone's browser push service (Google's, Apple's or Mozilla's, depending on the browser), encrypted end to end as the standard requires. The website has no accounts and no database and cannot see who paired or what is sent.
- **Calendar** writes an .ics file in Documents › Assignment Monitor on your PC. If you also enable invites, they go out by the email channel above.
