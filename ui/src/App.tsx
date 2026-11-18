import { useCallback, useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import {
  Award, BookOpen, CalendarCheck, CheckCheck, CheckCircle2, ChevronRight, GraduationCap, Info, ListChecks, Moon, RefreshCw,
  Search, Settings, Sun, Upload, XCircle,
} from 'lucide-react'
import { deleteSubmission, startSync, uploadFile, type Assignment } from './api'
import { Detail } from './Detail'
import { Palette, type Command } from './Palette'
import { ago, byDue, countdown, dueParts, initials, toneOf } from './format'
import { useEngine } from './useEngine'

type Filter = 'todo' | 'overdue' | 'submitted' | 'all'
type Toast = { id: number; ok: boolean; text: string }

const FILTERS: { key: Filter; label: string }[] = [
  { key: 'todo', label: 'To do' }, { key: 'overdue', label: 'Overdue' }, { key: 'submitted', label: 'Submitted' }, { key: 'all', label: 'All' },
]
const NAV = [
  { key: 'assignments', label: 'Assignments', icon: ListChecks }, { key: 'attendance', label: 'Attendance', icon: CalendarCheck },
  { key: 'exams', label: 'Exams', icon: GraduationCap }, { key: 'lectures', label: 'Lectures', icon: BookOpen },
  { key: 'results', label: 'Results', icon: Award }, { key: 'settings', label: 'Settings', icon: Settings },
]

const isTodo = (a: Assignment) => !a.is_submitted && a.urgency !== 'missed'
const isOverdue = (a: Assignment) => !a.is_submitted && a.urgency === 'missed'

function useTheme() {
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    try { const t = localStorage.getItem('am-theme'); if (t === 'light' || t === 'dark') return t } catch { /* private mode */ }
    return matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  })
  useEffect(() => {
    document.documentElement.dataset.theme = theme
    try { localStorage.setItem('am-theme', theme) } catch { /* private mode */ }
  }, [theme])
  return [theme, () => setTheme(t => (t === 'dark' ? 'light' : 'dark'))] as const
}

export default function App() {
  const { state, demo, running, run, now } = useEngine()
  const [theme, toggleTheme] = useTheme()
  const [filter, setFilter] = useState<Filter>('todo')
  const [course, setCourse] = useState('all')
  const [selId, setSelId] = useState<string | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])

  const all = state?.assignments ?? []
  const courses = useMemo(() => [...new Set(all.map(a => a.course))].sort(), [all])
  const counts = useMemo(() => ({
    todo: all.filter(isTodo).length, overdue: all.filter(isOverdue).length, submitted: all.filter(a => a.is_submitted).length, all: all.length,
  }), [all])
  const urgentCount = all.filter(a => !a.is_submitted && (a.urgency === 'today' || a.urgency === 'soon')).length

  const visible = useMemo(() => {
    const pick = ({ todo: isTodo, overdue: isOverdue, submitted: (a: Assignment) => a.is_submitted, all: () => true })[filter]
    return all.filter(a => pick(a) && (course === 'all' || a.course === course)).sort(byDue)
  }, [all, filter, course])

  const groups = useMemo(() => {
    const g: { title: string; items: Assignment[] }[] = []
    const add = (title: string, items: Assignment[]) => { if (items.length) g.push({ title, items }) }
    add('Due today', visible.filter(a => !a.is_submitted && a.urgency === 'today'))
    add('Coming up', visible.filter(a => !a.is_submitted && (a.urgency === 'soon' || a.urgency === 'week')))
    add('Later', visible.filter(a => !a.is_submitted && (a.urgency === 'later' || a.urgency === 'unknown')))
    add('Overdue', visible.filter(isOverdue).reverse())
    add('Submitted', visible.filter(a => a.is_submitted).reverse())
    return g
  }, [visible])

  const next = useMemo(() => all.filter(a => a.open && !a.is_submitted).sort(byDue)[0], [all])
  const sel = all.find(a => a.id === selId) ?? null
  const order = useMemo(() => groups.flatMap(g => g.items.map(a => a.id)), [groups])

  const toast = useCallback((ok: boolean, text: string) => {
    const id = Date.now() + Math.random()
    setToasts(t => [...t, { id, ok, text }])
    setTimeout(() => setToasts(t => t.filter(x => x.id !== id)), 5200)
  }, [])

  const doSync = useCallback(async () => {
    if (demo) return toast(false, 'Sample data: start the engine to check the portal.')
    const r = await run('sync', startSync)
    toast(r.ok, r.message || (r.ok ? 'Checked.' : 'The check did not finish.'))
  }, [demo, run, toast])

  const doUpload = async (a: Assignment, file: File, replace: boolean) => {
    const r = await run('upload', () => uploadFile(a.id, file, replace), a.id)
    toast(r.ok, r.ok ? `${a.title}: ${r.message}` : `${a.title} was not uploaded. ${r.message}${r.deleted ? ' Your previous submission was already deleted, so upload again before the deadline.' : ''}`)
  }
  const doDelete = async (a: Assignment) => {
    const r = await run('delete', () => deleteSubmission(a.id), a.id)
    toast(r.ok, r.ok ? `${a.title}: ${r.message}` : `${a.title}: ${r.message}`)
  }

  // keyboard: Ctrl/Cmd+K or / search, j/k move, u upload, Esc close
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement
      const typing = t instanceof HTMLInputElement || t instanceof HTMLTextAreaElement || t instanceof HTMLSelectElement
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); setPaletteOpen(o => !o); return }
      if (typing || paletteOpen || e.ctrlKey || e.metaKey || e.altKey) return
      if (e.key === '/') { e.preventDefault(); setPaletteOpen(true) }
      else if (e.key === 'Escape') setSelId(null)
      else if (e.key === 'j' || e.key === 'ArrowDown' || e.key === 'k' || e.key === 'ArrowUp') {
        e.preventDefault()
        const step = e.key === 'j' || e.key === 'ArrowDown' ? 1 : -1
        const i = selId ? order.indexOf(selId) : -1
        const to = order[Math.min(order.length - 1, Math.max(0, i + step))]
        if (to) setSelId(to)
      } else if (e.key === 'u' && selId) window.dispatchEvent(new Event('am:pick'))
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [paletteOpen, order, selId])

  useEffect(() => {
    if (selId) document.getElementById(`row-${CSS.escape(selId)}`)?.scrollIntoView({ block: 'nearest' })
  }, [selId])

  const commands: Command[] = [
    { id: 'cmd-sync', label: 'Check the portal now', icon: 'sync', run: () => void doSync() },
    { id: 'cmd-theme', label: theme === 'dark' ? 'Switch to the light theme' : 'Switch to the dark theme', icon: 'theme', run: toggleTheme },
  ]

  const busy = !!running
  const meta = state?.meta
  const nextTone = next ? toneOf(next.urgency) : 'later'

  return (
    <div className="app">
      {busy && <div className="topline" role="progressbar" aria-label="Working" />}

      <nav className="rail" aria-label="Main">
        <div className="brand">
          <svg className="brand-mark" viewBox="0 0 32 32" aria-hidden>
            <rect width="32" height="32" rx="9" fill="var(--ink)" />
            <circle cx="16" cy="16" r="8" fill="none" stroke="var(--canvas)" strokeWidth="2.4" />
            <path d="M12.5 16.2l2.6 2.6 4.6-5.2" fill="none" stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <div><b>Assignment Monitor</b><span>Bahria University</span></div>
        </div>
        <div className="nav">
          {NAV.map(n => (
            <button key={n.key} className="nav-item" disabled={n.key !== 'assignments'} aria-current={n.key === 'assignments' ? 'page' : undefined}>
              <n.icon aria-hidden /><span>{n.label}</span>
              {n.key === 'assignments' ? (urgentCount > 0 && <span className="nav-badge" aria-label={`${urgentCount} due soon`}>{urgentCount}</span>) : <span className="soon">Soon</span>}
            </button>
          ))}
        </div>
        <div className="rail-foot">
          <div className="me">
            <div className="avatar" aria-hidden>{initials(meta?.student_name)}</div>
            <div style={{ minWidth: 0 }}><b>{meta?.student_name ?? 'Student'}</b><span>{meta?.semester ?? ''}</span></div>
            <button className="icon-btn" style={{ marginLeft: 'auto' }} onClick={toggleTheme} aria-label={theme === 'dark' ? 'Use the light theme' : 'Use the dark theme'}>
              {theme === 'dark' ? <Sun /> : <Moon />}
            </button>
          </div>
        </div>
      </nav>

      <div className={`stage${sel ? ' with-panel' : ''}`}>
        <main className="page">
          <div className="page-inner">
            {demo && state && (
              <div className="banner" role="status"><Info aria-hidden /><span>Showing sample data. The engine is not running, so nothing here is yours yet.</span></div>
            )}

            <header className="topbar">
              <div>
                <h1>Assignments</h1>
                <p>{meta?.semester ? `${meta.semester} · ` : ''}checked {ago(meta?.last_sync, now)}</p>
              </div>
              <div className="actions">
                <button className="search-trigger" onClick={() => setPaletteOpen(true)} aria-label="Search and commands">
                  <Search aria-hidden /><span>Search</span><span className="kbd">Ctrl K</span>
                </button>
                <button className="btn btn-quiet" onClick={() => void doSync()} disabled={busy}>
                  <RefreshCw aria-hidden className={running?.kind === 'sync' ? 'spin' : ''} />{running?.kind === 'sync' ? 'Checking…' : 'Check now'}
                </button>
              </div>
            </header>

            {!state ? (
              <div aria-busy="true" style={{ display: 'grid', gap: 12 }}>
                <div className="skeleton" style={{ height: 168 }} />
                {[0, 1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 56 }} />)}
              </div>
            ) : (
              <>
                {next ? (
                  <motion.section className={`focus tone-${nextTone}`} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
                    transition={{ type: 'spring', stiffness: 160, damping: 22 }} aria-label="Up next">
                    <div>
                      <div className="eyebrow">{next.urgency === 'today' ? 'Due today' : 'Up next'}</div>
                      <h2>{next.title}</h2>
                      <div className="meta">{next.course} · {dueParts(next.due_at).day}{dueParts(next.due_at).time && ` at ${dueParts(next.due_at).time}`}</div>
                    </div>
                    <div className="count" aria-label={`${countdown(next.due_at, now).big} left`}>
                      <div className="big mono">{countdown(next.due_at, now).big}</div>
                      <div className="unit">{countdown(next.due_at, now).unit}</div>
                    </div>
                    <div className="focus-actions">
                      <button className="btn btn-primary btn-lg" onClick={() => setSelId(next.id)}><Upload aria-hidden />{next.can_upload ? 'Upload your work' : 'Open'}</button>
                      <span style={{ color: 'var(--muted)', fontSize: 'var(--t-sm)' }}>{counts.todo > 1 ? `${counts.todo - 1} more to do after this` : 'Nothing else is waiting'}</span>
                    </div>
                  </motion.section>
                ) : (
                  <section className="caught-up" aria-label="All caught up">
                    <CheckCheck aria-hidden />
                    <div><b>You are all caught up</b><span>{all.length ? 'Nothing is waiting for you. New work shows up here as soon as the portal lists it.' : 'No assignments yet. They appear here once the portal lists them.'}</span></div>
                  </section>
                )}

                <div className="toolbar">
                  <div className="seg" role="group" aria-label="Show">
                    {FILTERS.map(f => (
                      <button key={f.key} aria-pressed={filter === f.key} onClick={() => setFilter(f.key)}>{f.label}<span className="n">{counts[f.key]}</span></button>
                    ))}
                  </div>
                  {courses.length > 1 && (
                    <select className="select" value={course} onChange={e => setCourse(e.target.value)} aria-label="Course">
                      <option value="all">All courses</option>
                      {courses.map(c => <option key={c} value={c}>{c}</option>)}
                    </select>
                  )}
                </div>

                {groups.length === 0 ? (
                  <div className="empty"><b>Nothing here</b>{filter === 'todo' ? 'You have no open assignments in this view.' : 'No assignments match this view.'}</div>
                ) : groups.map(g => (
                  <section key={g.title} className="group" aria-label={g.title}>
                    <div className="group-head">{g.title}<span className="n">{g.items.length}</span></div>
                    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
                      {g.items.map((a, i) => {
                        const tone = toneOf(a.urgency)
                        const d = dueParts(a.due_at)
                        return (
                          <motion.li key={a.id} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }}
                            transition={{ delay: Math.min(i, 8) * 0.025, type: 'spring', stiffness: 220, damping: 26 }}>
                            <button id={`row-${a.id}`} className={`row tone-${tone}`} aria-current={a.id === selId ? 'true' : undefined} onClick={() => setSelId(a.id === selId ? null : a.id)}>
                              <span className="dot" aria-hidden />
                              <span style={{ minWidth: 0 }}>
                                <span className="row-title" style={{ display: 'block' }}>{a.title}</span>
                                <span className="row-sub" style={{ display: 'block' }}>{a.course} · #{a.assign_no}</span>
                              </span>
                              <span className="row-end">
                                {(a.can_upload || a.can_replace) && <span className="quick pill tone-week">{a.can_replace ? 'Replace' : 'Upload'}</span>}
                                {a.is_submitted
                                  ? <span className="pill tone-ok"><CheckCircle2 aria-hidden />Submitted</span>
                                  : a.urgency === 'missed'
                                    ? <span className="pill tone-urgent"><XCircle aria-hidden />Overdue</span>
                                    : <span className="when mono">{d.day}<small>{d.time}</small></span>}
                                <ChevronRight aria-hidden style={{ width: 16, height: 16, color: 'var(--faint)' }} />
                              </span>
                            </button>
                          </motion.li>
                        )
                      })}
                    </ul>
                  </section>
                ))}
              </>
            )}
          </div>
        </main>

        {sel && (
          <Detail key={sel.id} a={sel} now={now} demo={demo} running={running} onClose={() => setSelId(null)}
            onUpload={(f, r) => void doUpload(sel, f, r)} onDelete={() => void doDelete(sel)} />
        )}
      </div>

      <AnimatePresence>
        {paletteOpen && (
          <Palette assignments={all} commands={commands} onClose={() => setPaletteOpen(false)} onPick={id => setSelId(id)} />
        )}
      </AnimatePresence>

      <div className="toasts" aria-live="polite">
        <AnimatePresence>
          {toasts.map(t => (
            <motion.div key={t.id} className={`toast ${t.ok ? 'ok' : 'bad'}`} initial={{ opacity: 0, y: 12, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8 }} transition={{ type: 'spring', stiffness: 320, damping: 28 }}>
              {t.ok ? <CheckCircle2 aria-hidden /> : <XCircle aria-hidden />}<span>{t.text}</span>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </div>
  )
}
