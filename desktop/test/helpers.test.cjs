'use strict'
const test = require('node:test')
const assert = require('node:assert/strict')
const path = require('node:path')
const { hashForView, parseCli, parseReadyLine, isSafeExternalUrl, resolveAppPath, mimeFor, CSP, boundsOnScreen } = require('../lib/helpers.cjs')

test('the engine ready line is parsed, and anything else is ignored', () => {
  assert.deepEqual(parseReadyLine('{"port": 51234, "token": "abc123"}\n'), { port: 51234, token: 'abc123' })
  for (const bad of ['', 'hello', '{"port": 0, "token": "abc"}', '{"port": 70000, "token": "abc"}', '{"port": "80", "token": "abcdef"}', '{"port": 80}', '{"port": 80, "token": "x"}', '[1]'])
    assert.equal(parseReadyLine(bad), null, bad)
})

test('only https and mail links ever reach the system browser', () => {
  assert.equal(isSafeExternalUrl('https://github.com/Nobody243/Assignment_Monitor'), true)
  assert.equal(isSafeExternalUrl('mailto:a@b.co'), true)
  for (const bad of ['http://example.com', 'file:///C:/Windows/System32/calc.exe', 'javascript:alert(1)', 'app://bundle/', 'ms-msdt:/id', 'not a url', ''])
    assert.equal(isSafeExternalUrl(bad), false, bad)
})

test('the app protocol stays inside the built interface', () => {
  const root = path.resolve('C:/app/ui/dist')
  assert.equal(resolveAppPath(root, '/'), path.join(root, 'index.html'))
  assert.equal(resolveAppPath(root, '/assets/index-abc.js'), path.join(root, 'assets', 'index-abc.js'))
  assert.equal(resolveAppPath(root, '/assets/app.css?v=1#x'), path.join(root, 'assets', 'app.css'))
  for (const bad of ['/../secret.txt', '/..%2Fsecret.txt', '/assets/../../secret.txt', '/%2e%2e/secret', '/a\0b', '/%E0%A4%A'])
    assert.equal(resolveAppPath(root, bad), null, bad)
})

test('file types are served with the right type', () => {
  assert.match(mimeFor('x.js'), /javascript/)
  assert.match(mimeFor('x.CSS'), /css/)
  assert.equal(mimeFor('x.woff2'), 'font/woff2')
  assert.equal(mimeFor('x.unknown'), 'application/octet-stream')
})

test('the content security policy is closed by default', () => {
  assert.match(CSP, /default-src 'self'/)
  assert.match(CSP, /script-src 'self'(;|$)/)                      // no inline or remote scripts
  assert.match(CSP, /object-src 'none'/)
  assert.match(CSP, /connect-src 'self' http:\/\/127\.0\.0\.1:\*/)    // the local engine, nothing else
  assert.doesNotMatch(CSP, /unsafe-eval/)
})

test('a saved window position is used only while it is still on a screen', () => {
  const displays = [{ workArea: { x: 0, y: 0, width: 1920, height: 1040 } }]
  assert.equal(boundsOnScreen({ x: 100, y: 80, width: 1200, height: 800 }, displays), true)
  assert.equal(boundsOnScreen({ x: 1800, y: 60, width: 1200, height: 800 }, displays), false)     // mostly off the right edge
  assert.equal(boundsOnScreen({ x: 3000, y: 100, width: 1200, height: 800 }, displays), false)    // a monitor that is gone
  assert.equal(boundsOnScreen({ x: -4000, y: 0, width: 1200, height: 800 }, displays), false)
  assert.equal(boundsOnScreen(null, displays), false)
  assert.equal(boundsOnScreen({ x: NaN, y: 0, width: 10, height: 10 }, displays), false)
})

test('the old command line still means what it did', () => {
  assert.deepEqual(parseCli(['--check', '--quiet', '--junk']), { headless: true, passthrough: ['--check', '--quiet'], quit: false, tray: false, setup: false, view: null })
  assert.equal(parseCli(['--remind', '--test']).passthrough.join(' '), '--remind --test')
  assert.equal(parseCli(['--enable-automation']).headless, true)
  const gui = parseCli(['--tray', '--view', 'attendance'])
  assert.deepEqual([gui.headless, gui.tray, gui.view], [false, true, 'attendance'])
  assert.equal(parseCli(['--view', 'not-a-page']).view, null)
  assert.equal(parseCli(['--setup']).view, 'settings')
  assert.equal(parseCli(['--quit']).quit, true)
  assert.equal(parseCli([]).headless, false)
})

test('--view names map to the interface pages', () => {
  assert.equal(hashForView('assignments'), '#/assignments')
  assert.equal(hashForView('dashboard'), '')
  assert.equal(hashForView('activity'), '#/settings/activity')
  assert.equal(hashForView(null, true), '#/settings/profile')
})
