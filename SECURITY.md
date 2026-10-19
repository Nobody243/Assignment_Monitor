# Security

## What the app does with your data

| Data | Where it lives | Protection |
| --- | --- | --- |
| Portal password | `%LOCALAPPDATA%\Assignment Monitor\settings.env` | Encrypted with Windows DPAPI for your user account. Another user or another PC cannot decrypt it. Never written to the log. |
| Enrollment number, campus, preferences | same file | Plain text (not secret). |
| Assignment list, sync metadata, log | `%LOCALAPPDATA%\Assignment Monitor\data\` | Local files, readable only by your Windows account by default. |
| Browser profile (portal session cookies) | `%LOCALAPPDATA%\Assignment Monitor\chrome_profile\` | Local, same as above. Deleted on uninstall. |

Running from source, the same files live in the project folder and are git-ignored.

## Network

- The app only connects to `https://cms.bahria.edu.pk` and `https://lms.bahria.edu.pk`, over HTTPS, to do exactly what you would do by hand: sign in, open the LMS, open the assignments page for each course.
- If Google Chrome is not installed, Playwright's Chromium is downloaded once from Microsoft's Playwright CDN.
- "Check for updates" opens the GitHub releases page in your browser. The app itself does not phone home, has no telemetry, and sends nothing anywhere else.

## Design choices

- No server, no accounts: nothing of yours is stored outside your PC.
- Background tasks run as your own Windows user, with your normal privileges; the installer and the app never ask for administrator rights.
- One sync at a time: a lock file prevents the scheduled task and the window from signing in simultaneously.
- Dependencies are pinned in `requirements.txt` and audited in CI with `pip-audit`.
- The executable is not code-signed (that costs money), so Windows SmartScreen warns on first run. You can verify what you run by building from source with `python build.py`.

## Reporting a problem

Open an issue on GitHub or, for something sensitive, use GitHub's private vulnerability reporting on the repository. Please include the app version (Settings → About) and the log excerpt from the Activity tab with any personal details removed.
