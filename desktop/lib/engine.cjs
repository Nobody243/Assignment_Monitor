'use strict'
// Starts the Python engine as a child process and hands back where to reach it.
const { spawn } = require('node:child_process')
const path = require('node:path')
const fs = require('node:fs')
const { parseReadyLine } = require('./helpers.cjs')

/** Which program runs the engine: an explicit override, the bundled executable of an installed build, or Python from the source tree. */
function engineCommand({ root, resourcesPath, packaged }) {
  if (process.env.AM_ENGINE_EXE) return { cmd: process.env.AM_ENGINE_EXE, args: [], cwd: path.dirname(process.env.AM_ENGINE_EXE) }
  if (packaged) {
    const exe = path.join(resourcesPath, 'engine', 'AssignmentEngine.exe')
    if (fs.existsSync(exe)) return { cmd: exe, args: [], cwd: path.dirname(exe) }
  }
  return { cmd: process.env.AM_PYTHON || 'python', args: [path.join(root, 'engine.py')], cwd: root }
}

/**
 * Starts the engine with the shell's origin allowed and "exit when my stdin closes", so it can never outlive the shell.
 * Resolves with { port, token, proc, stop() } once the engine has printed its ready line.
 */
function startEngine({ command, origins, onExit, env = {}, timeoutMs = 30000 }) {
  return new Promise((resolve, reject) => {
    const args = [...command.args, ...origins.flatMap(o => ['--origin', o]), '--exit-on-stdin-close']
    let proc
    try {
      proc = spawn(command.cmd, args, { cwd: command.cwd, stdio: ['pipe', 'pipe', 'pipe'], windowsHide: true, env: { ...process.env, ...env } })
    } catch (e) { return reject(new Error(`Could not start ${command.cmd}: ${e.message}`)) }
    let done = false
    let out = ''
    let err = ''
    const timer = setTimeout(() => fail(new Error('The engine did not become ready in time.')), timeoutMs)
    const fail = e => { if (done) return; done = true; clearTimeout(timer); try { proc.kill() } catch { /* already gone */ } reject(Object.assign(e, { stderr: err.slice(-1500) })) }

    proc.on('error', e => fail(new Error(e.code === 'ENOENT' ? `Python was not found (${command.cmd}). Install Python 3.11 or set AM_PYTHON.` : e.message)))
    proc.stderr.on('data', d => { err = (err + d).slice(-4000) })
    proc.stdout.on('data', d => {
      out += d
      let i
      while ((i = out.indexOf('\n')) >= 0) {
        const line = out.slice(0, i)
        out = out.slice(i + 1)
        const ready = parseReadyLine(line)
        if (ready && !done) {
          done = true
          clearTimeout(timer)
          const stop = () => new Promise(res => {
            if (proc.exitCode !== null) return res()
            const kill = setTimeout(() => { try { proc.kill() } catch { /* gone */ } }, 3000)
            proc.once('exit', () => { clearTimeout(kill); res() })
            try { proc.stdin.end() } catch { /* already closed */ }
          })
          resolve({ ...ready, proc, stop })
        }
      }
    })
    proc.on('exit', (code, signal) => {
      if (!done) return fail(new Error(`The engine stopped before it was ready (${signal || `exit code ${code}`}).`))
      if (onExit) onExit(code, signal)
    })
  })
}

/** Runs a background job (--check, --remind, ...) through the engine and resolves with its exit code. No window, no service. */
function runJob({ command, args, env = {} }) {
  return new Promise(resolve => {
    let proc
    try { proc = spawn(command.cmd, [...command.args, ...args], { cwd: command.cwd, stdio: 'inherit', windowsHide: true, env: { ...process.env, ...env } }) } catch { return resolve(1) }
    proc.on('error', () => resolve(1))
    proc.on('exit', code => resolve(code ?? 1))
  })
}

module.exports = { engineCommand, runJob, startEngine }
