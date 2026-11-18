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

module.exports = { parseReadyLine, isSafeExternalUrl, resolveAppPath, mimeFor, CSP, boundsOnScreen }
