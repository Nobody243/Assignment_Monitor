import { useSyncExternalStore } from 'react'

/** Every outcome the interface reports (an upload, a check, a setting, a failure) is kept here, so nothing that
 *  happened is lost once its toast disappears. Kept on this computer only. */
export type Entry = { id: string; at: number; ok: boolean; title: string; detail?: string }

const KEY = 'am-activity'
const MAX = 200
const subs = new Set<() => void>()

function load(): Entry[] {
  try { const v = JSON.parse(localStorage.getItem(KEY) ?? '[]'); return Array.isArray(v) ? v : [] } catch { return [] }
}
let entries: Entry[] = load()
const emit = () => subs.forEach(f => f())
const persist = () => { try { localStorage.setItem(KEY, JSON.stringify(entries)) } catch { /* private mode */ } }

export function record(e: Omit<Entry, 'id' | 'at'>) {
  entries = [{ id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, at: Date.now(), ...e }, ...entries].slice(0, MAX)
  persist(); emit()
}
export function clearActivity() { entries = []; persist(); emit() }
export const useActivity = () => useSyncExternalStore(f => { subs.add(f); return () => subs.delete(f) }, () => entries)
export const activitySnapshot = () => entries
