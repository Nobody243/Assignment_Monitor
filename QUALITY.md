# Quality

How Assignment Monitor is built and checked, laid out against the eight product-quality characteristics of
ISO/IEC 25010, with the evidence for each. This is a description of practice, not a certificate.

**What is not claimed.** ISO 9001, CMMI and Six Sigma certify an organisation's processes through audits and
measured defect rates. Assignment Monitor is an open-source project with one maintainer; it is not certified
against any of them and does not claim to be. ISO/IEC 25010 is a vocabulary for assessing a product, which is what
this document uses.

## The process behind every release

- Every change is committed to the public repository with a message that says what changed and why.
- Every commit runs the linter (ruff) and the unit test suite in GitHub Actions on Windows; a failing test blocks
  the build. The suite has 135 tests at 1.6.1: parsers against saved portal HTML, deadline logic, the tracker's
  change detection, channels, calendar export, the updater, the cloud workflow, automation task XML, crash
  handling, failure counting, and a GUI smoke test that opens the real window and runs its pages.
- Releases are built by GitHub Actions from a tagged commit, never from a developer's machine, so the installer
  matches the source anyone can read. Release notes come from CHANGELOG.md.
- A clean-machine test installs each release on a fresh Windows runner with Google Chrome hidden, registers the
  background tasks, runs a test alert, runs a real check (so the app must fetch its own browser engine), captures
  the first-run window, and uninstalls, checking that nothing is left behind.
- Before a release with user-visible changes, the real window is driven on a real account through every page and
  action (sync, filters, exports, downloads, alerts, settings), with every Tk error collected.
- The dependency set is audited for published vulnerabilities on every build (pip-audit).

## ISO/IEC 25010 characteristics

### Functional suitability
- Covers what students asked for: assignments with extended-deadline detection, attendance margins against a
  minimum, exam seating, announcements, lecture and miscellaneous files, timetable, results with GPA and CGPA, assignment files (brief,
  own submission, returned work, solution), delivered by voice, Windows notification, phone push, email and
  calendar, on the PC and from the cloud with the PC off.
- Parsers are tested against saved copies of the portal's real HTML, and the portal is read live on every
  release by the clean-machine test and the account-level run.
- Known limit: the portal's layout is outside the project's control; a change there can stop a reader. Repeated
  failures are counted and reported (see Reliability) so the maintainer hears quickly.

### Reliability
- Background checks that fail are counted; a portal outage is reported after three failures in a row, a
  rejected sign-in once, and the Dashboard shows the count against the last good check.
- Three cloud failures in a row produce one notification pointing at the run log.
- Errors inside the window surface in a dialog with the error text, a copy button, the log and a pre-filled
  issue; the packaged app used to swallow them.
- Between semesters (no courses on the portal) every page says so instead of showing stale data; nothing is
  deleted.
- Scheduled tasks wake the PC, run on battery, restart on failure and are re-registered when their format is
  out of date.

### Performance efficiency
- A full check reads every course of a semester in about two minutes on a home connection; the cloud check in
  under a minute on GitHub's machines.
- Pages are rebuilt only when their data changed; long lists are built lazily as the user scrolls.
- The website: Lighthouse desktop 90 performance on the home page and 85 on the download page (the 3D globe is
  the cost, accepted for the visual), 100 accessibility, 100 best practices, 100 SEO; layout shift below 0.03.

### Usability
- One-time sign-in, then nothing to do: the app runs itself. Every alert says what changed and where.
- The window fits 1366x768 laptops at 125 % scaling and 1024x768 screens; checked by capture at those sizes.
- Light and dark themes; keyboard shortcuts for every page, sync and search; a crash dialog instead of a
  silent failure; plain-language empty states and errors.
- Website: zero serious or critical accessibility violations on every route (axe), one heading per page,
  alternative text on every image, phone layouts checked at 360, 390 and 430 px.

### Security
- The portal password is encrypted with Windows DPAPI for the signed-in user; the enrollment number is masked
  in the log. Nothing is sent to any server of the project's; there is none.
- The optional cloud check stores the login as GitHub Actions secrets in the student's own private repository,
  encrypted by GitHub, masked in logs; the app says so before asking consent and removes them when turned off,
  including from the uninstaller.
- Downloads are fetched only from GitHub's release hosts (allow-listed) over HTTPS. The website sends a strict
  Content-Security-Policy, HSTS, nosniff, frame denial and a referrer policy, serves its own fonts, and makes no
  third-party request on a normal visit.
- Security reporting policy: SECURITY.md. Known limit: the installer is not yet code-signed (application with
  SignPath pending), so Windows SmartScreen warns on first run.

### Compatibility
- Windows 10 and 11, with or without Google Chrome (a browser engine is fetched when Chrome is absent;
  verified on a clean machine).
- Phone alerts work through the phone's browser (Android Chrome and Samsung Internet, iOS 16.4+ as a Home
  Screen app) with no app to install.
- Reads only the student's own pages, exactly as a browser would; never writes to the portal.

### Maintainability
- One repository, plain Python and a small React site, no server to operate. Modules are separated by concern
  (scraper, tracker, notifier, channels, cloud, automation, updater, UI).
- 135 automated tests, lint on every commit, a changelog entry for every release, and a documented release
  process. Lessons from live failures are turned into tests (the lecture download, the sign-in race, the
  GUI smoke test).
- Issues are the public channel; the crash dialog and the 404 page pre-fill them with the facts needed.

### Portability
- Installer and portable zip, both built by CI. Silent install and uninstall work for managed machines.
  Settings and data live in one folder under the user's profile; the uninstaller offers to remove them.
- The clean-machine test is the portability check that runs on every release.

## Automated checks and their last readings

Run on 25 October 2026 against 1.6.0 and 1.6.1 (the first three run in GitHub Actions on every commit).

| Check | Tool | Reading |
|---|---|---|
| Style and correctness lint | ruff | clean |
| Security lint | Bandit (medium and above) | clean: every opened URL is checked to be https; content hashes are declared non-security |
| Dependency vulnerabilities | pip-audit on requirements.txt | none |
| Unit and GUI tests | pytest | 135 passed |
| Test coverage | coverage.py | 49 % of statements overall; the pure logic is high (results 96 %, tracker 94 %, campus parsers 93 %, deadlines 99 %), the window and the live portal reader are low (app 40 %, scraper 22 %) and are covered by the clean-machine run and the account-level run instead |
| Complexity | radon | no function above grade D except the Dashboard's refresh (E); the Results page's recompute was F and was split into five steps |
| Website accessibility | axe-core, Lighthouse | 0 serious or critical violations on every route; Lighthouse accessibility 100 desktop and mobile |
| Website performance | Lighthouse | desktop: home 85, download 91, FAQ 94, guide 91; mobile home 41 (the 3D globe, an accepted trade-off) |
| Website SEO and best practices | Lighthouse | 100 and 100 on every page measured |
| HTML validity | W3C Nu validator | 0 errors, 0 warnings on every page |
| Security headers | curl | CSP, HSTS, nosniff, frame denial, referrer and permissions policies all present |

## Honest gaps

- No independent audit or certification of any kind.
- One maintainer; reviews are self-reviews plus the automated checks.
- The portal has no API; the app depends on its HTML, which can change without notice.
- The installer is unsigned until SignPath approves the application.

Last reviewed with release 1.6.1, 25 October 2026.
