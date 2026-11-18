import { useCallback, useEffect, useRef, useState } from 'react'
import { getJob, getState, type Job, type State } from './api'
import { DEMO } from './demo'

export type Running = { kind: string; assignmentId?: string; step: string }
export type Outcome = { ok: boolean; message: string; deleted?: boolean; folder?: string }

/** Loads the engine's state, falls back to labelled demo data when it cannot be reached, and runs one action at a time
 *  (the engine enforces that too), polling its progress. */
export function useEngine() {
  const [state, setState] = useState<State | null>(null)
  const [demo, setDemo] = useState(false)
  const [running, setRunning] = useState<Running | null>(null)
  const [now, setNow] = useState(() => Date.now())
  const runningRef = useRef<Running | null>(null)
  runningRef.current = running

  const refresh = useCallback(async () => {
    try {
      setState(await getState())
      setDemo(false)
    } catch {
      setState(s => s ?? DEMO)
      setDemo(true)
    }
  }, [])

  useEffect(() => { void refresh() }, [refresh])
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
    setRunning({ kind, assignmentId, step: 'Starting…' })
    try {
      const { job } = await begin()
      for (;;) {
        await new Promise(r => setTimeout(r, 600))
        const j: Job = await getJob(job)
        setRunning({ kind, assignmentId, step: j.step })
        if (j.status === 'done') {
          await refresh()
          return j.result ?? { ok: false, message: 'No result.' }
        }
      }
    } catch (e) {
      return { ok: false, message: e instanceof Error ? e.message : 'It did not work.' }
    } finally {
      setRunning(null)
    }
  }, [refresh])

  return { state, demo, running, run, now, refresh }
}
