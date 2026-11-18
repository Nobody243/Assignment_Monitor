'use strict'
// Runs before the interface loads, in an isolated context. It gives the page two read-only facts and nothing else:
// where the engine is (and the key to it), and that it is running inside the desktop shell.
const { contextBridge } = require('electron')

const arg = process.argv.find(a => a.startsWith('--am-engine='))
if (arg) {
  try {
    const cfg = JSON.parse(arg.slice('--am-engine='.length))
    contextBridge.exposeInMainWorld('__ENGINE__', Object.freeze({ base: String(cfg.base), token: String(cfg.token) }))
  } catch { /* the page then shows its "cannot reach the engine" screen */ }
}
contextBridge.exposeInMainWorld('__SHELL__', Object.freeze({ name: 'electron', platform: process.platform, version: process.versions.electron }))
