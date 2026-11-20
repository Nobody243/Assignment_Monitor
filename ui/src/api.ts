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
export type AttendanceSession = { date: string; type: string; room?: string; remarks?: string; topics?: string; hours: number; present: number; absent: number }
export type AttendanceCourse = {
  code: string; title: string; present: number; absent: number; recorded: boolean; percent: number; ok: boolean; can_miss: number; need: number
  teacher?: string; class?: string; credit_hours?: string; sessions?: AttendanceSession[]
}
export type Attendance = { minimum: number; overall: number | null; courses: AttendanceCourse[] }
export type TimetableSession = { day: string; start: string; end: string; course: string; abbr: string; teacher: string; initials: string }
export type Standing = { semester: string; gpa: number | null; cgpa: number; semesters: number; series: { name: string; gpa: number | null; cgpa: number | null }[] }
export type Exam = {
  title: string; date: string; start_time?: string; room?: string; exam_type?: string; session?: string; row?: string; column?: string
  scheduled?: boolean; status?: string; fee_defaulter?: boolean; surveys?: string; class?: string
}
export type LectureFile = { label: string; href: string; filename: string }
export type Lecture = {
  id: string; course: string; week: string | number; title: string; files: LectureFile[]; videos?: unknown[]; remarks?: string
  first_seen?: string; kind?: 'misc'
}
export type Announcement = { id: string; course: string; title: string; text: string; posted: string; posted_at?: string; first_seen?: string; semester?: string }
export type ResultCourse = { code: string; title: string; credits: number; grade: string; points: number | null; product: number | null }
export type ResultSemester = { name: string; courses: ResultCourse[]; gpa: number | null; cgpa: number | null; complete: boolean }
export type Results = { student?: Record<string, string>; semesters: ResultSemester[] } | null
export type State = {
  version: string; now: string; meta: Meta; assignments: Assignment[]
  attendance: Attendance; exams: Exam[]; exams_all: Exam[]; announcements: Announcement[]; lectures: Lecture[]; results: Results
  timetable: { semester?: string; sessions?: TimetableSession[] }; standing: Standing | null; paths: { lectures: string; data: string }
}
export type Job = { id: string; kind: string; status: 'running' | 'done'; step: string; result: { ok: boolean; message: string; deleted?: boolean; folder?: string; url?: string; repo?: string } | null }

type EngineCfg = { base: string; token: string }
const cfg: EngineCfg = (window as unknown as { __ENGINE__?: EngineCfg }).__ENGINE__ ?? { base: 'http://127.0.0.1:8765', token: 'dev' }

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(cfg.base + path, {
    ...init,
    headers: { Authorization: `Bearer ${cfg.token}`, ...(init.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const b = body as { error?: string; errors?: Record<string, string> }
    throw new Error(b.error ?? (b.errors ? Object.values(b.errors).join('; ') : `Request failed (${res.status})`))
  }
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

export type FileKind = 'brief' | 'submission' | 'returned' | 'solution' | 'all'
export const downloadAssignmentFiles = (id: string, kind: FileKind = 'all') =>
  call<{ job: string }>(`/api/assignments/download?id=${encodeURIComponent(id)}&kind=${kind}`, { method: 'POST' })
export const downloadLectures = (ids: string[]) =>
  call<{ job: string }>('/api/lectures/download', { method: 'POST', body: JSON.stringify({ ids }), headers: { 'Content-Type': 'application/json' } })
export const saveTimetable = (format: 'png' | 'jpg' | 'pdf', theme: 'light' | 'dark') =>
  call<{ ok: boolean; file: string; folder: string }>(`/api/timetable/save?format=${format}&theme=${theme}`, { method: 'POST' })
export const openFolder = (kind: 'lectures' | 'data' | 'timetable') => call<{ ok: boolean; folder: string }>(`/api/open-folder?kind=${kind}`, { method: 'POST' })

// ------------------------------------------------------------------------------------------------ settings
export type SettingsView = {
  account: { enrollment: string; institute_id: string; campus: string; password_set: boolean }
  appearance: { animations: boolean }
  setup_done?: boolean
  about: { version: string; tagline: string; installed: boolean; repo: string; site: string; author: string; license: string }
  campuses: { id: string; name: string }[]
  alerts: { voice: boolean; toast: boolean; notify_days_ahead: number; voice_name: string; voice_volume: number; voice_rate: number }
  tracking: {
    track_attendance: boolean; track_exams: boolean; track_announcements: boolean; track_lectures: boolean; track_timetable: boolean; track_results: boolean
    attendance_min: number; exam_remind_days: number; remind_leads: number[]
  }
  background: { close_to_tray: boolean; check_updates: boolean; lectures_dir: string; downloads_default: string; starts_with_windows: boolean; automatic_checks: boolean; owned_by_installed_app: boolean }
  channels: {
    email_enabled: boolean; email_to: string; email_pass_set: boolean; email_host: string; email_port: number
    push_enabled: boolean; push_paired: boolean; push_device: string; calendar_enabled: boolean; calendar_invites: boolean
  }
  cloud: { available: boolean; enabled: boolean; repo: string; login: string }
}
export type CloudStatus = { enabled: boolean; login?: string; repo?: string; last?: { when: string; status: string; conclusion: string | null; url: string }; error?: string }

const post = <T,>(path: string, body?: unknown) =>
  call<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body), headers: body === undefined ? undefined : { 'Content-Type': 'application/json' } })

export const getSettings = () => call<SettingsView>('/api/settings')
export const patchSettings = (patch: Record<string, unknown>) => post<{ changed: string[]; settings: SettingsView }>('/api/settings', patch)
export const verifyAccount = () => post<{ job: string }>('/api/account/verify')
export const setAutomation = (on: boolean) => post<{ job: string }>(`/api/automation?enable=${on ? 1 : 0}`)
export const setStartup = (on: boolean) => post<{ ok: boolean; starts_with_windows: boolean }>(`/api/startup?enable=${on ? 1 : 0}`)
export const testAlert = () => post<{ ok: boolean }>('/api/test/alert')
export const testEmail = () => post<{ job: string }>('/api/test/email')
export const testPush = () => post<{ job: string }>('/api/test/push')
export const getVoices = () => call<{ voices: string[] }>('/api/voices')
export const previewVoice = (v: { voice_name: string; voice_volume: number; voice_rate: number }) => post<{ ok: boolean }>('/api/voice/preview', v)
export const pairStart = () => post<{ url: string; code: string; qr: string }>('/api/pair/start')
export const pairPoll = () => post<{ status: 'waiting' | 'opened' | 'paired'; device?: string }>('/api/pair/poll')
export const pairCancel = () => post<{ ok: boolean }>('/api/pair/cancel')
export const unpair = () => post<{ ok: boolean }>('/api/unpair')
export const cloudStart = () => post<{ user_code: string; verification_uri: string; interval: number; expires_in: number }>('/api/cloud/start')
export const cloudPoll = () => post<{ status: 'pending' | 'ready'; interval?: number }>('/api/cloud/poll')
export const cloudSetup = () => post<{ job: string }>('/api/cloud/setup')
export const cloudDisable = () => post<{ job: string }>('/api/cloud/disable')
export const cloudRun = () => post<{ ok: boolean }>('/api/cloud/run')
export const getCloudStatus = () => call<CloudStatus>('/api/cloud/status')
export const clearData = () => post<{ ok: boolean }>('/api/data/clear')

export type LogEntry = { time: string; level: string; text: string }
export const getLog = (lines = 300) => call<{ entries: LogEntry[] }>(`/api/log?lines=${lines}`)

export type UpdateInfo = { version?: string; newer?: boolean; page?: string; current?: string; error?: string }
export const getUpdate = () => call<UpdateInfo>('/api/update')
export const installUpdate = () => post<{ job: string }>('/api/update/install')
