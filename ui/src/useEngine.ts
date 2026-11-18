import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob, getState, type Job, type State } from './api'
import { DEMO } from './demo'

export type Running = { kind: string; assignmentId?: string; step: string }
export type Outcome = { ok: boolean; message: string; deleted?: boolean; folder?: string; url?: string; repo?: string }
export type Connection = 'connecting' | 'online' | 'offline'

const RETRY_SECONDS = 6
const REFRESH_MS = 60_000

/** Loads the engine's state and keeps it fresh. When the engine cannot be reached it says so (and retries by itself)
 *  instead of quietly swapping in sample data; sample data is shown only if the user asks for it. Also runs one
 *  action at a time (the engine enforces that too) and follows its progress. */
export function useEngine() {
  const [real, setReal] = useState<State | null>(null)
  const [connection, setConnection] = useState<Connection>('connecting')
  const [wantDemo, setWantDemo] = useState(false)
  const [retryIn, setRetryIn] = useState<number | null>(null)
  const [lastGood, setLastGood] = useState<number | null>(null)
  const [lastError, setLastError] = useState('')
  const [running, setRunning] = useState<Running | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const runningRef = useRef<Running | null>(null)
  const mark = useCallback((r: Running | null) => { runningRef.current = r; setRunning(r) }, [])

  const refresh = useCallback(async (quiet = false) => {
    if (!quiet) setConnection(c => (c === 'online' ? c : 'connecting'))
    try {
      setReal(await getState())
      setConnection('online')
      setLastGood(Date.now())
      setLastError('')
      setRetryIn(null)
    } catch (e) {
      setConnection('offline')
      setRetryIn(RETRY_SECONDS)                   // a failed try starts the next countdown
      setLastError(e instanceof TypeError ? 'no answer from the engine' : e instanceof Error ? e.message : 'unknown error')
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])

  // offline: count down and try again by itself; online: refresh quietly so a background check shows up on its own
  useEffect(() => {
    if (connection === 'offline') {
      setRetryIn(RETRY_SECONDS)
      const t = setInterval(() => setRetryIn(s => (s == null ? null : Math.max(0, s - 1))), 1000)
      return () => clearInterval(t)
    }
    if (connection === 'online') {
      const t = setInterval(() => { if (!runningRef.current) void refresh(true) }, REFRESH_MS)
      return () => clearInterval(t)
    }
  }, [connection, refresh])
  useEffect(() => { if (connection === 'offline' && retryIn === 0) void refresh(true) }, [connection, retryIn, refresh])

  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 30_000)
    return () => clearInterval(t)
  }, [])

  // an upload or delete must not be cut off half way: ask the browser/shell before the window closes
  useEffect(() => {
    const guard = (e: BeforeUnloadEvent) => { if (runningRef.current) e.preventDefault() }
    window.addEventListener('beforeunload', guard)
    return () => window.removeEventListener('beforeunload', guard)
  }, [])

  /** Starts an action (the caller passes the function that begins the job) and resolves with its outcome. */
  const run = useCallback(async (kind: string, begin: () => Promise<{ job: string }>, assignmentId?: string): Promise<Outcome> => {
    if (runningRef.current) return { ok: false, message: 'Another action is still running.' }
    mark({ kind, assignmentId, step: 'Starting…' })
    try {
      const { job } = await begin()
      for (;;) {
        await new Promise(r => setTimeout(r, 600))
        const j: Job = await getJob(job)
        mark({ kind, assignmentId, step: j.step })
        if (j.status === 'done') {
          await refresh(true)
          return j.result ?? { ok: false, message: 'No result.' }
        }
      }
    } catch (e) {
      const offline = e instanceof TypeError
      if (offline) setConnection('offline')
      return { ok: false, message: offline ? 'The engine stopped answering. Check that the app is still running.' : e instanceof Error ? e.message : 'It did not work.' }
    } finally {
      mark(null)
    }
  }, [refresh, mark])

  const state = real ?? (wantDemo ? DEMO : null)
  return {
    state,
    demo: !real && wantDemo,
    connection,
    stale: connection === 'offline' && !!real,   // had real data, lost the engine
    retryIn,
    lastGood,
    lastError,
    retry: () => void refresh(),
    showDemo: () => setWantDemo(true),
    leaveDemo: () => { setWantDemo(false); void refresh() },
    running, run, now, refresh,
  }
}
