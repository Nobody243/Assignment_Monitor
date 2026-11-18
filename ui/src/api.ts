// The interface talks to the app's engine (engine.py) over loopback HTTP. In development the engine runs with
// `python engine.py --dev` (port 8765, token "dev"); in the packaged app the shell injects window.__ENGINE__.
export type Urgency = 'today' | 'soon' | 'week' | 'later' | 'missed' | 'submitted' | 'unknown'

export type Assignment = {
  id: string
  course: string
  assign_no: string
  title: string
  due_date: string
  due_at: string | null
  urgency: Urgency
  label: string
  days: number | null
  is_submitted: boolean
  is_extended?: boolean
  original_due_date?: string
  marks?: string
  action: string
  open: boolean
  can_upload: boolean
  can_replace: boolean
  files?: Record<string, { href: string; label: string; filename: string }>
}

export type Meta = { student_name?: string; semester?: string; courses?: string[]; last_sync?: string | null; enrollment?: string }
export type AttendanceCourse = { code: string; title: string; present: number; absent: number; recorded: boolean; percent: number; ok: boolean; can_miss: number; need: number }
export type Attendance = { minimum: number; overall: number | null; courses: AttendanceCourse[] }
export type TimetableSession = { day: string; start: string; end: string; course: string; abbr: string; teacher: string; initials: string }
export type Standing = { semester: string; gpa: number | null; cgpa: number; semesters: number }
export type State = {
  version: string; now: string; meta: Meta; assignments: Assignment[]
  attendance: Attendance; timetable: { semester?: string; sessions?: TimetableSession[] }; standing: Standing | null
}
export type Job = { id: string; kind: string; status: 'running' | 'done'; step: string; result: { ok: boolean; message: string; deleted?: boolean } | null }

type EngineCfg = { base: string; token: string }
const cfg: EngineCfg = (window as unknown as { __ENGINE__?: EngineCfg }).__ENGINE__ ?? { base: 'http://127.0.0.1:8765', token: 'dev' }

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(cfg.base + path, {
    ...init,
    headers: { Authorization: `Bearer ${cfg.token}`, ...(init.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) throw new Error((body as { error?: string }).error ?? `Request failed (${res.status})`)
  return body as T
}

export const getState = () => call<State>('/api/state')
export const getJob = (id: string) => call<Job>(`/api/jobs/${id}`)
export const startSync = () => call<{ job: string }>('/api/sync', { method: 'POST' })
export const deleteSubmission = (id: string) =>
  call<{ job: string }>(`/api/assignments/delete?id=${encodeURIComponent(id)}`, { method: 'POST' })
export const uploadFile = (id: string, file: File, replace: boolean) =>
  call<{ job: string }>(`/api/assignments/upload?id=${encodeURIComponent(id)}&replace=${replace ? 1 : 0}`, {
    method: 'POST',
    headers: { 'X-Filename': file.name, 'Content-Type': 'application/octet-stream' },
    body: file,
  })

export const MAX_BYTES = 15 * 1024 * 1024
export const ALLOWED = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip']
/** The same rules the engine applies, so a wrong file is turned away before anything is sent. */
export function checkFile(f: File): string {
  const ext = f.name.slice(f.name.lastIndexOf('.')).toLowerCase()
  if (!ALLOWED.includes(ext)) return `The portal accepts only ${ALLOWED.join(', ')} files.`
  if (f.size === 0) return 'That file is empty.'
  if (f.size > MAX_BYTES) return `That file is ${(f.size / 1048576).toFixed(1)} MB; the portal's limit is 15 MB.`
  return ''
}
