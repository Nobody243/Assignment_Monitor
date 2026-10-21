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
| [Inter](https://rsms.me/inter/) | user-interface typeface, bundled unmodified in `assets/fonts` | SIL Open Font License 1.1 (`assets/fonts/LICENSE-Inter.txt`) |
| [PyInstaller](https://pyinstaller.org/) | builds the executable (build-time only) | GPL with bootloader exception; the built app is not affected |
| [Inno Setup](https://jrsoftware.org/isinfo.php) | builds the installer (build-time only) | Inno Setup License |
| Google Chrome / Chromium | the browser that opens the portal (Chrome if installed, otherwise Chromium downloaded by Playwright) | Google Chrome ToS / BSD |

The Windows speech synthesizer, DPAPI and Task Scheduler are part of Windows.
