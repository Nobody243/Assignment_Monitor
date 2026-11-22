'use strict'
// Small pure functions the main process leans on, kept apart so they can be tested without starting Electron.
const path = require('node:path')

/** The engine prints one JSON line when it is ready: {"port": 51234, "token": "..."}. */
function parseReadyLine(line) {
  try {
    const o = JSON.parse(String(line).trim())
    if (Number.isInteger(o.port) && o.port > 0 && o.port < 65536 && typeof o.token === 'string' && o.token.length >= 3) return { port: o.port, token: o.token }
  } catch { /* not the ready line */ }
  return null
}

/** Only https links (and mail links) may be handed to the system browser; nothing else is ever opened. */
function isSafeExternalUrl(raw) {
  try {
    const u = new URL(raw)
    return u.protocol === 'https:' || u.protocol === 'mailto:'
  } catch { return false }
}

/** Maps a request path to a file inside `root`, or null when it would escape it (.. segments, encoded or not). */
function resolveAppPath(root, urlPath) {
  let p
  try { p = decodeURIComponent(String(urlPath).split('?')[0].split('#')[0]) } catch { return null }
  if (p.includes('\0')) return null
  p = p.replace(/^[\\/]+/, '')
  if (!p) p = 'index.html'
  const full = path.resolve(root, p)
  const rel = path.relative(root, full)
  if (rel.startsWith('..') || path.isAbsolute(rel)) return null
  return full
}

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png',
  '.jpg': 'image/jpeg', '.ico': 'image/x-icon', '.woff2': 'font/woff2', '.woff': 'font/woff', '.txt': 'text/plain; charset=utf-8', '.map': 'application/json',
}
const mimeFor = file => MIME[path.extname(file).toLowerCase()] || 'application/octet-stream'

// What the interface may do: run its own scripts and styles, show its own images and fonts, and talk to the local engine and nothing else.
const CSP = [
  "default-src 'self'", "script-src 'self'", "style-src 'self' 'unsafe-inline'", "img-src 'self' data: blob:", "font-src 'self' data:",
  'connect-src \'self\' http://127.0.0.1:*', "object-src 'none'", "base-uri 'none'", "frame-src 'none'", "form-action 'none'",
].join('; ')

/** A saved window position is used only if enough of it is still on a screen (a monitor may have been unplugged). */
function boundsOnScreen(b, displays) {
  if (!b || !Number.isFinite(b.x) || !Number.isFinite(b.y) || !Number.isFinite(b.width) || !Number.isFinite(b.height)) return false
  return displays.some(d => {
    const w = d.workArea
    const ox = Math.min(b.x + b.width, w.x + w.width) - Math.max(b.x, w.x)
    const oy = Math.min(b.y + b.height, w.y + w.height) - Math.max(b.y, w.y)
    return ox >= 200 && oy >= 120
  })
}

const HEADLESS_FLAGS = ['--check', '--remind', '--status', '--test-alert', '--enable-automation', '--disable-automation', '--disable-cloud']
const HEADLESS_MODIFIERS = ['--test', '--quiet', '-q', '--visible']
const VIEWS = ['dashboard', 'assignments', 'attendance', 'exams', 'results', 'timetable', 'announcements', 'lectures', 'settings', 'activity']

/**
 * The command line the app has always understood (scheduled tasks and shortcuts use it). A background job
 * (--check, --remind, ...) is handed to the engine and never opens a window; the rest steer the window.
 */
function parseCli(argv) {
  const has = f => argv.includes(f)
  const link = argv.find(a => /^assignment-monitor:\/\//i.test(a))          // a button on a reminder notification
  const headless = HEADLESS_FLAGS.some(has) || !!link
  const i = argv.indexOf('--view')
  const view = i >= 0 && VIEWS.includes(argv[i + 1]) ? argv[i + 1] : null
  return {
    headless,
    passthrough: headless ? [...argv.filter(a => HEADLESS_FLAGS.includes(a) || HEADLESS_MODIFIERS.includes(a)), ...(link ? ['--toast-action', link] : [])] : [],
    quit: has('--quit'), tray: has('--tray'), setup: has('--setup'),
    view: has('--setup') ? 'settings' : view,
  }
}

/** The page hash for a --view name; names that are not pages of their own land on Home. */
function hashForView(view, setup) {
  if (setup) return '#/settings/profile'
  if (view === 'activity') return '#/settings/activity'
  if (!view || view === 'dashboard') return ''
  return `#/${view}`
}

/**
 * What the tray icon says: how many unsubmitted, still-open assignments are due within a day, and the next one.
 * `assignments` are the engine's records ({title, is_submitted, open, due_at}); `now` is a time in milliseconds.
 */
function trayStatus(assignments, now) {
  const soon = (assignments || [])
    .filter(a => a && a.open && !a.is_submitted && a.due_at && Number.isFinite(Date.parse(a.due_at)))
    .map(a => ({ title: String(a.title || 'Assignment'), left: Date.parse(a.due_at) - now }))
    .filter(a => a.left > 0)
    .sort((x, y) => x.left - y.left)
  const dueToday = soon.filter(a => a.left <= 24 * 3600e3)
  const next = soon[0]
  const phrase = ms => { const h = ms / 3600e3; return h < 1 ? `${Math.max(1, Math.round(h * 60))} min` : h < 48 ? `${Math.round(h)} h` : `${Math.round(h / 24)} days` }
  const lines = ['Assignment Monitor']
  if (dueToday.length) lines.push(`${dueToday.length} due within a day`)
  lines.push(next ? `Next: ${next.title.slice(0, 40)} in ${phrase(next.left)}` : 'Nothing due soon')
  return { count: dueToday.length, tooltip: lines.join('\n') }
}

/** Paints a red dot with a white ring in the bottom-right of a BGRA bitmap (a copy is returned), for the tray and taskbar badge. */
function paintBadge(bitmap, width, height) {
  const out = Buffer.from(bitmap)
  const r = Math.max(3, Math.round(Math.min(width, height) * 0.28))
  const cx = width - r - 1, cy = height - r - 1
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const d = Math.hypot(x - cx + 0.5, y - cy + 0.5)
      if (d > r + 1.2) continue
      const i = (y * width + x) * 4
      const ring = d > r - 1.2
      out[i] = ring ? 255 : 51; out[i + 1] = ring ? 255 : 51; out[i + 2] = ring ? 255 : 220; out[i + 3] = 255     // B G R A
    }
  }
  return out
}

/** The window's own colour, shown before the interface has painted anything: the theme last used in the interface (it follows
 *  the system until the person picks one), so a dark-theme launch does not flash light. Colours match the page backgrounds. */
const WINDOW_BACKGROUND = { light: '#eef1f6', dark: '#0f1116' }
function windowBackground(savedTheme, systemDark) {
  const theme = savedTheme === 'dark' || savedTheme === 'light' ? savedTheme : (systemDark ? 'dark' : 'light')
  return WINDOW_BACKGROUND[theme]
}

module.exports = { windowBackground, WINDOW_BACKGROUND, paintBadge, trayStatus, hashForView, parseCli, parseReadyLine, isSafeExternalUrl, resolveAppPath, mimeFor, CSP, boundsOnScreen }
