# Third-party software

Assignment Monitor is MIT licensed. The installed app bundles these open-source components; each keeps its own license.

| Component | Use | License |
| --- | --- | --- |
| [Python](https://www.python.org/) 3.x | runtime | PSF License |
| [Playwright for Python](https://github.com/microsoft/playwright-python) + Node driver | signs in to the portal in a real browser | Apache License 2.0 |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | user interface | CC0 1.0 / MIT (see project) |
| [pystray](https://github.com/moses-palmer/pystray) | system tray icon | LGPL v3. Bundled unmodified as replaceable Python files under `_internal/pystray`, so you may swap in your own copy. |
| [Pillow](https://python-pillow.org/) | loads the tray icon image | MIT-CMU (HPND) |
| [lxml](https://lxml.de/) | parses the assignments table | BSD 3-Clause |
| [winotify](https://github.com/versa-syahptr/winotify) | Windows notifications | MIT |
| [pywebpush](https://github.com/web-push-libs/pywebpush), [py-vapid](https://github.com/web-push-libs/vapid) | sends the optional phone pushes (Web Push with VAPID) | MPL 2.0 |
| [http-ece](https://github.com/web-push-libs/encrypted-content-encoding) | encrypts push payloads (RFC 8291) | MIT |
| [cryptography](https://cryptography.io/) | the push keys and the pairing encryption | Apache License 2.0 / BSD |
| [requests](https://requests.readthedocs.io/) | HTTP client used by pywebpush | Apache License 2.0 |
| [qrcode](https://github.com/lincolnloop/python-qrcode) | draws the pairing QR code | BSD 3-Clause |
| [PyNaCl](https://github.com/pyca/pynacl) (bundles libsodium) | seals the cloud-check secrets for GitHub (libsodium sealed box) | Apache License 2.0 (PyNaCl) / ISC (libsodium) |
| [Inter](https://rsms.me/inter/) | user-interface typeface, bundled unmodified in `assets/fonts` | SIL Open Font License 1.1 (`assets/fonts/LICENSE-Inter.txt`) |
| [PyInstaller](https://pyinstaller.org/) | builds the executable (build-time only) | GPL with bootloader exception; the built app is not affected |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | builds the installer (build-time only) | Inno Setup License |
| Google Chrome / Chromium | the browser that opens the portal (Chrome if installed, otherwise Chromium downloaded by Playwright) | Google Chrome ToS / BSD |

The Windows speech synthesizer, DPAPI and Task Scheduler are part of Windows. Email uses Python's standard library (smtplib) and your own mail server.
