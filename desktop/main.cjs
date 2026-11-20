'use strict'
const path = require('node:path')
const fs = require('node:fs')
const { pathToFileURL } = require('node:url')
const { app, BrowserWindow, Menu, Tray, dialog, nativeImage, net, protocol, screen, session, shell } = require('electron')
const { CSP, boundsOnScreen, hashForView, isSafeExternalUrl, mimeFor, parseCli, resolveAppPath } = require('./lib/helpers.cjs')
const { engineCommand, runJob, startEngine } = require('./lib/engine.cjs')

const CLI = parseCli(process.argv.slice(app.isPackaged ? 1 : 2))      // the command line the app has always understood
const SMOKE = process.argv.includes('--smoke')
const DEV = process.argv.includes('--dev')
const DEV_URL = process.env.AM_DEV_URL || 'http://localhost:5173'
const SCHEME = 'app'
const APP_ORIGIN = `${SCHEME}://bundle`
const ROOT = path.resolve(__dirname, '..')                                   // the repository (unpackaged) or app resources
const UI_DIR = app.isPackaged ? path.join(process.resourcesPath, 'ui') : path.join(ROOT, 'ui', 'dist')
const ICON = app.isPackaged ? path.join(process.resourcesPath, 'assets', 'icon.ico') : path.join(ROOT, 'assets', 'icon.ico')

protocol.registerSchemesAsPrivileged([{ scheme: SCHEME, privileges: { standard: true, secure: true, supportFetchAPI: true, corsEnabled: true } }])

let win = null
let tray = null
let engine = null                  // { port, token, stop }
let quitting = false
let closeToTray = true             // refreshed from the engine's settings
let restarts = []
let settingsTimer = null

// Scheduled tasks and shortcuts must start THIS program, so the engine is told which one it is (an installed build only)
const engineEnv = () => (app.isPackaged ? { AM_SHELL_EXE: process.execPath } : {})

const pageOrigin = () => (DEV ? new URL(DEV_URL).origin : APP_ORIGIN)

// ------------------------------------------------------------------------------------------------ window state
const statePath = () => path.join(app.getPath('userData'), 'window-state.json')
function loadState() {
  try {
    const s = JSON.parse(fs.readFileSync(statePath(), 'utf8'))
    return boundsOnScreen(s, screen.getAllDisplays()) ? s : null
  } catch { return null }
}
function saveState() {
  if (!win || win.isDestroyed() || win.isMinimized()) return
  try {
    const b = win.getNormalBounds()
    fs.writeFileSync(statePath(), JSON.stringify({ ...b, maximized: win.isMaximized() }))
  } catch { /* the position is a convenience, never a failure */ }
}

// ------------------------------------------------------------------------------------------------ the app:// protocol serves ui/dist
function registerAppProtocol() {
  protocol.handle(SCHEME, async request => {
    const url = new URL(request.url)
    let file = resolveAppPath(UI_DIR, url.pathname)
    if (!file) return new Response('Not found', { status: 404 })
    if (!fs.existsSync(file) || fs.statSync(file).isDirectory()) file = path.join(UI_DIR, 'index.html')   // hash routing: one page
    const res = await net.fetch(pathToFileURL(file).toString())
    return new Response(res.body, { status: res.status, headers: { 'Content-Type': mimeFor(file), 'Content-Security-Policy': CSP, 'Cache-Control': 'no-store' } })
  })
}

// ------------------------------------------------------------------------------------------------ engine
async function ensureEngine() {
  for (;;) {
    try {
      const origins = [pageOrigin()]
      engine = await startEngine({
        command: engineCommand({ root: ROOT, resourcesPath: process.resourcesPath, packaged: app.isPackaged }),
        origins, env: engineEnv(),
        onExit: (code, signal) => { if (!quitting) void onEngineGone(code, signal) },
      })
      return
    } catch (e) {
      if (SMOKE) throw e
      const choice = dialog.showMessageBoxSync({
        type: 'error', title: 'Assignment Monitor', buttons: ['Try again', 'Quit'], defaultId: 0, cancelId: 1,
        message: 'The app engine could not start.', detail: `${e.message}${e.stderr ? `\n\n${e.stderr}` : ''}`,
      })
      if (choice === 1) { quitting = true; app.quit(); throw e }
    }
  }
}

/** The engine ended without being asked to: start it again (a few times), and give the window its new address and key. */
async function onEngineGone(code, signal) {
  const now = Date.now()
  restarts = restarts.filter(t => now - t < 60000)
  restarts.push(now)
  if (restarts.length > 3) {
    dialog.showErrorBox('Assignment Monitor', `The app engine keeps stopping (${signal || `exit code ${code}`}). Close and reopen the app.`)
    quitting = true
    app.quit()
    return
  }
  engine = null
  try {
    await ensureEngine()
    if (win && !win.isDestroyed()) { win.destroy(); win = null }
    createWindow()
  } catch { /* ensureEngine already told the user */ }
}

function pollSettings() {
  const ask = async () => {
    if (!engine) return
    try {
      const r = await fetch(`http://127.0.0.1:${engine.port}/api/settings`, { headers: { Authorization: `Bearer ${engine.token}` } })
      if (r.ok) closeToTray = !!(await r.json()).background?.close_to_tray
    } catch { /* keep the last value */ }
  }
  void ask()
  settingsTimer = setInterval(ask, 30000)
}

// ------------------------------------------------------------------------------------------------ window
function createWindow() {
  const saved = loadState()
  win = new BrowserWindow({
    width: saved?.width ?? 1360, height: saved?.height ?? 860, x: saved?.x, y: saved?.y, minWidth: 900, minHeight: 620,
    show: false, title: 'Assignment Monitor', icon: ICON, backgroundColor: '#eef1f6', autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'), contextIsolation: true, nodeIntegration: false, sandbox: true, webSecurity: true,
      spellcheck: false, devTools: DEV || SMOKE,
      additionalArguments: [`--am-engine=${JSON.stringify({ base: `http://127.0.0.1:${engine.port}`, token: engine.token })}`],
    },
  })
  if (saved?.maximized) win.maximize()
  if (!SMOKE && !CLI.tray) win.once('ready-to-show', () => win.show())

  // links: https opens in the browser; the window itself never leaves the interface
  const wc = win.webContents
  wc.setWindowOpenHandler(({ url }) => { if (isSafeExternalUrl(url)) void shell.openExternal(url); return { action: 'deny' } })
  wc.on('will-navigate', (e, url) => {
    if (new URL(url).origin === pageOrigin()) return
    e.preventDefault()
    if (isSafeExternalUrl(url)) void shell.openExternal(url)
  })
  // the interface holds back a close while an upload or delete is half way: ask, so the user decides
  wc.on('will-prevent-unload', e => {
    const choice = dialog.showMessageBoxSync(win, {
      type: 'question', buttons: ['Keep working', 'Close anyway'], defaultId: 0, cancelId: 0, title: 'Assignment Monitor',
      message: 'An action is still running.', detail: 'Closing now could leave an upload or a delete half done.',
    })
    if (choice === 1) e.preventDefault()          // preventing the prevention lets the window close
  })

  // the page process died (crash, out of memory): load the interface again instead of leaving a blank window
  wc.on('render-process-gone', (_e, details) => {
    if (details.reason === 'clean-exit' || quitting || SMOKE) return
    setTimeout(() => { if (win && !win.isDestroyed()) void win.loadURL(DEV ? DEV_URL : `${APP_ORIGIN}/`) }, 500)
  })

  win.on('close', e => {
    saveState()
    if (!quitting && closeToTray && tray) { e.preventDefault(); win.hide() }
  })
  win.on('closed', () => { win = null })
  win.on('resize', saveState)
  win.on('move', saveState)

  void win.loadURL((DEV ? DEV_URL : `${APP_ORIGIN}/`) + hashForView(CLI.view, CLI.setup))
  if (DEV) wc.openDevTools({ mode: 'detach' })
  return win
}

function showWindow() {
  if (!win || win.isDestroyed()) return createWindow()
  if (win.isMinimized()) win.restore()
  win.show()
  win.focus()
}

function createTray() {
  try {
    tray = new Tray(nativeImage.createFromPath(ICON))
  } catch { tray = null; return }
  tray.setToolTip('Assignment Monitor')
  tray.setContextMenu(Menu.buildFromTemplate([
    { label: 'Open Assignment Monitor', click: showWindow },
    { label: 'Check now', click: () => { if (engine) void fetch(`http://127.0.0.1:${engine.port}/api/sync`, { method: 'POST', headers: { Authorization: `Bearer ${engine.token}` } }).catch(() => {}) } },
    { type: 'separator' },
    { label: 'Quit', click: () => { quitting = true; app.quit() } },
  ]))
  tray.on('click', showWindow)
}

// ------------------------------------------------------------------------------------------------ smoke: start everything for real, look at the page, report, exit
async function smoke() {
  const fail = msg => { process.stdout.write(`SMOKE_RESULT ${JSON.stringify({ ok: false, error: msg })}\n`); quitting = true; app.exit(1) }
  const timer = setTimeout(() => fail('timed out after 90 s'), 90000)
  try {
    await new Promise(resolve => win.webContents.once('did-finish-load', resolve))
    const result = await win.webContents.executeJavaScript(`(async () => {
      for (let i = 0; i < 100 && !document.querySelector('h1'); i++) await new Promise(r => setTimeout(r, 200))
      const cfg = window.__ENGINE__
      const st = cfg ? await (await fetch(cfg.base + '/api/state', { headers: { Authorization: 'Bearer ' + cfg.token } })).json() : null
      const bad = cfg ? await fetch(cfg.base + '/api/state').then(r => r.status).catch(() => 'blocked') : null
      return { title: document.title, h1: document.querySelector('h1')?.innerText ?? null, origin: location.origin, hasEngine: !!cfg, shell: window.__SHELL__?.name ?? null,
               leaks: typeof window.require + '/' + typeof window.process, assignments: st ? st.assignments.length : null, noTokenStatus: bad,
               nodeInPage: typeof require !== 'undefined' }
    })()`)
    if (process.env.AM_SMOKE_SHOT) {          // a picture of what the window really shows, for a person to look at
      await new Promise(r => setTimeout(r, 1500))
      fs.writeFileSync(process.env.AM_SMOKE_SHOT, (await win.webContents.capturePage()).toPNG())
    }
    clearTimeout(timer)
    process.stdout.write(`SMOKE_RESULT ${JSON.stringify({ ok: true, ...result })}\n`)
    quitting = true
    await engine?.stop()
    app.exit(0)
  } catch (e) { clearTimeout(timer); fail(String(e && e.message || e)) }
}

// ------------------------------------------------------------------------------------------------ start
if (CLI.headless) {
  // a scheduled task or a shortcut asked for a background job: the engine does it, no window, no tray, no single-instance lock
  void app.whenReady().then(async () => {
    const code = await runJob({ command: engineCommand({ root: ROOT, resourcesPath: process.resourcesPath, packaged: app.isPackaged }), args: CLI.passthrough, env: engineEnv() })
    app.exit(code)
  })
} else if (!app.requestSingleInstanceLock()) {
  app.quit()            // the running instance hears our command line (--quit, --view ...) through its 'second-instance' event
} else if (CLI.quit) {
  app.exit(1)           // asked to quit a running instance, but none is running
} else {
  app.on('second-instance', (_e, argv) => {
    const cmd = parseCli(argv.slice(app.isPackaged ? 1 : 2))
    if (cmd.quit) { quitting = true; app.quit(); return }
    showWindow()
    if (win && (cmd.view || cmd.setup)) void win.webContents.executeJavaScript(`location.hash = ${JSON.stringify(hashForView(cmd.view, cmd.setup))}`)
  })
  app.setAppUserModelId('com.nobody243.assignmentmonitor')

  app.whenReady().then(async () => {
    Menu.setApplicationMenu(DEV ? Menu.buildFromTemplate([{ label: 'View', submenu: [{ role: 'reload' }, { role: 'toggleDevTools' }, { role: 'quit' }] }]) : null)
    session.defaultSession.setPermissionRequestHandler((_wc, permission, cb) => cb(permission === 'clipboard-sanitized-write'))
    session.defaultSession.setPermissionCheckHandler((_wc, permission) => permission === 'clipboard-sanitized-write')
    if (!DEV) registerAppProtocol()
    try { await ensureEngine() } catch (e) { if (SMOKE) { process.stdout.write(`SMOKE_RESULT ${JSON.stringify({ ok: false, error: e.message, stderr: e.stderr })}\n`); app.exit(1) } return }
    createWindow()
    if (SMOKE) return void smoke()
    createTray()
    pollSettings()
  })

  // every web contents, present or future: no <webview>, no popups, no navigation away from the app's own origin
  app.on('web-contents-created', (_e, contents) => {
    contents.on('will-attach-webview', e => e.preventDefault())
    contents.setWindowOpenHandler(({ url }) => { if (isSafeExternalUrl(url)) void shell.openExternal(url); return { action: 'deny' } })
    contents.on('will-navigate', (e, url) => {
      let same = false
      try { same = new URL(url).origin === pageOrigin() } catch { /* not a URL */ }
      if (!same) e.preventDefault()
    })
  })

  app.on('before-quit', () => { quitting = true })
  app.on('window-all-closed', () => { /* the tray keeps the app alive; Quit in the tray menu ends it */ if (!tray) app.quit() })
  app.on('will-quit', e => {
    clearInterval(settingsTimer)
    if (engine) {
      e.preventDefault()
      const eng = engine
      engine = null
      void eng.stop().finally(() => app.exit(0))
    }
  })
}
