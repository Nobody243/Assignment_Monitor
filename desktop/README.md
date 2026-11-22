# Assignment Monitor: desktop shell

A thin Electron shell around the new interface (`../ui`) and the Python engine (`../engine.py`).

```
Electron main process (main.cjs)
 ├─ starts the engine:  python engine.py --origin app://bundle --exit-on-stdin-close
 │    prints {"port","token"} once; the engine exits by itself when the shell closes or dies
 ├─ serves ../ui/dist at app://bundle (path-checked, with a strict Content-Security-Policy)
 └─ opens one sandboxed window; preload.cjs gives the page only the engine address + key
```

## Run it

```bash
cd ui && npm install && npm run build      # once, and after changing the interface
cd ../desktop && npm install
npm start                                   # the app
npm run dev                                 # against the Vite dev server (http://localhost:5173) with DevTools
npm run smoke                               # headless: starts everything, checks the page, prints SMOKE_RESULT, exits
npm test                                    # unit tests for the shell's safety rules
```

`AM_PYTHON` picks another Python; `AM_ENGINE_EXE` runs a bundled engine executable instead; `AM_SMOKE_SHOT=file.png` makes
`npm run smoke` save a screenshot of what the window really shows.

## What it does

- **Security:** context isolation and sandbox on, no Node in the page, navigation locked to the app's own origin, only `https`
  links are handed to the system browser, all permission requests refused, the engine needs a random per-launch key and only
  answers the shell's origin.
- **Engine:** restarted (up to three times a minute) if it dies, with a fresh key and window; a clear error with Try again / Quit
  if it cannot start.
- **Window:** remembers its size and position (and ignores a position that is no longer on a screen), one instance only
  (a second launch focuses the first), a tray icon, and "keep running in the tray when closed" follows the app's own setting.
- **Closing mid-action:** if an upload or delete is running, the window asks before it closes.

## Building the installed app

```bash
python build_desktop.py        # from the repository root: interface, engine exe, shell folder, portable zip, installer, SHA-256
```

Steps it runs: `ui` build, `python build_engine.py` (PyInstaller, `dist/engine`), `npm run package` here (`@electron/packager`, then
the unused Electron features are switched off with fuses), then Inno Setup (`installer.iss`, same app id, name and per-user folder
as before, so existing installs update in place and old Tk files are removed). Tasks, shortcuts and the installer's `--quit`
keep working because the shell understands the old command line and hands background jobs (`--check`, `--remind`, ...) to the engine.

The packaged app was checked with `AssignmentMonitor.exe --smoke` and `--status` on fictional data (`tools/seed_demo_data.py`).
The installer itself is built and tested in CI (`desktop-build.yml`); it is not run on a developer machine, because it would replace
the real shortcuts and tasks.

## Releases and the in-app update check

Desktop releases are tagged `v1.9.7` and published automatically when a desktop change lands on `main` and its build passes
(`.github/workflows/auto-release-desktop.yml`). The phone app's releases live in the same repository, tagged `phone-v1.0.8`, so
GitHub's "latest release" could be either. Two rules keep the desktop app's update check right:

- the build marks each desktop release as the latest (`make_latest: true`), and the phone release never is;
- `updater.py` only ever offers a tag that looks like `v1.2.3`, and searches the release list when "latest" is not one.

## Not done yet

Code signing (the SignPath hook in `build.yml` still applies once the release build switches to `build_desktop.py`), and switching
`build.yml` from `python build.py` to `python build_desktop.py` when this branch becomes the release.
