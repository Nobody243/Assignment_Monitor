import { useEffect, useState } from 'react'
import { Bell, Volume2 } from 'lucide-react'
import { toast } from 'sonner'
import { getVoices, previewVoice, setAutomation, setStartup, testAlert, type SettingsView } from '@/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import type { Outcome } from '@/useEngine'
import { Row, Section, SwitchRow } from './parts'

type Save = (p: Record<string, unknown>) => Promise<boolean>
const DAYS = [0, 1, 2, 3, 5, 7, 10, 14]
const RATES = [{ v: -2, l: 'Slow' }, { v: 0, l: 'Normal' }, { v: 2, l: 'Fast' }]

export function AlertsSection({ view, save, demo }: { view: SettingsView; save: Save; demo: boolean }) {
  const al = view.alerts
  const [voices, setVoices] = useState<string[]>([])
  const [volume, setVolume] = useState(al.voice_volume)
  useEffect(() => { setVolume(al.voice_volume) }, [al.voice_volume])
  useEffect(() => { if (!demo) void getVoices().then(r => setVoices(r.voices)).catch(() => setVoices([])) }, [demo])
  const rate = RATES.some(r => r.v === al.voice_rate) ? al.voice_rate : 0
  const preview = () => void previewVoice({ voice_name: al.voice_name, voice_volume: volume, voice_rate: rate }).then(() => toast.info('Playing a preview…')).catch(e => toast.error(String(e.message ?? e)))
  return (
    <Section id="alerts" title="Notifications" description="How the app gets your attention after a check and in the hourly reminder.">
      <SwitchRow label="Windows notifications" hint="A pop-up from the notification area" checked={al.toast} onChange={v => void save({ toast: v })} />
      <SwitchRow label="Spoken reminders" hint="Reads the reminder aloud on the day something is due" checked={al.voice} onChange={v => void save({ voice: v })} />
      <Row label="Warn me ahead" hint="How far before a deadline alerts begin">
        <Select value={String(al.notify_days_ahead)} onValueChange={v => void save({ notify_days_ahead: Number(v) })}>
          <SelectTrigger size="sm" className="w-44" aria-label="Days ahead"><SelectValue /></SelectTrigger>
          <SelectContent>{(DAYS.includes(al.notify_days_ahead) ? DAYS : [...DAYS, al.notify_days_ahead].sort((a, b) => a - b)).map(d => <SelectItem key={d} value={String(d)}>{d === 0 ? 'Same day only' : d === 1 ? '1 day ahead' : `${d} days ahead`}</SelectItem>)}</SelectContent>
        </Select>
      </Row>
      <Row label="Voice" hint="A speech voice installed on this PC">
        <Select value={al.voice_name || 'default'} onValueChange={v => void save({ voice_name: v === 'default' ? '' : v })}>
          <SelectTrigger size="sm" className="w-56" aria-label="Voice"><SelectValue /></SelectTrigger>
          <SelectContent><SelectItem value="default">Default</SelectItem>{voices.map(v => <SelectItem key={v} value={v}>{v}</SelectItem>)}</SelectContent>
        </Select>
      </Row>
      <Row label="Volume" hint={<span className="num">{volume}%</span>}>
        <Slider className="w-48" min={0} max={100} step={5} value={[volume]} onValueChange={v => setVolume(v[0])} onValueCommit={v => void save({ voice_volume: v[0] })} aria-label="Volume" />
      </Row>
      <Row label="Speed">
        <Select value={String(rate)} onValueChange={v => void save({ voice_rate: Number(v) })}>
          <SelectTrigger size="sm" className="w-32" aria-label="Speed"><SelectValue /></SelectTrigger>
          <SelectContent>{RATES.map(r => <SelectItem key={r.v} value={String(r.v)}>{r.l}</SelectItem>)}</SelectContent>
        </Select>
      </Row>
      <div className="flex flex-wrap gap-2 pt-3">
        <Button variant="outline" size="sm" onClick={preview} disabled={demo}><Volume2 />Preview voice</Button>
        <Button variant="outline" size="sm" onClick={() => void testAlert().then(() => toast.info('Test alert sent.'))} disabled={demo}><Bell />Send a test alert</Button>
      </div>
    </Section>
  )
}

export function TrackingSection({ view, save }: { view: SettingsView; save: Save }) {
  const t = view.tracking
  const [min, setMin] = useState(t.attendance_min)
  useEffect(() => { setMin(t.attendance_min) }, [t.attendance_min])
  const items: [keyof SettingsView['tracking'], string, string][] = [
    ['track_attendance', 'Attendance', 'Read per course, with an alert when an absence is recorded'],
    ['track_exams', 'Exam seating', 'Dates, rooms and seats, with a reminder before each paper'],
    ['track_announcements', 'Announcements', 'Teacher posts on the LMS'],
    ['track_lectures', 'Lecture notes', 'New weeks and files, plus miscellaneous files'],
    ['track_timetable', 'Timetable', 'Your weekly classes'],
    ['track_results', 'Results', 'Your transcript, with an alert when a grade is posted'],
  ]
  return (
    <Section id="tracking" title="Campus tracking" description="What each check reads from the portal. Turn off what you do not use to make checks faster.">
      {items.map(([k, label, hint]) => <SwitchRow key={k} label={label} hint={hint} checked={t[k] as boolean} onChange={v => void save({ [k]: v })} />)}
      <Row label="Attendance minimum" hint="Courses below this are flagged. Your university's rule is usually 75%.">
        <span className="num w-10 text-right text-sm">{min}%</span>
        <Slider className="w-40" min={50} max={100} step={1} value={[min]} onValueChange={v => setMin(v[0])} onValueCommit={v => void save({ attendance_min: v[0] })} aria-label="Attendance minimum" />
      </Row>
      <Row label="Exam reminder" hint="When to remind you before each paper">
        <Select value={String(t.exam_remind_days)} onValueChange={v => void save({ exam_remind_days: Number(v) })}>
          <SelectTrigger size="sm" className="w-44" aria-label="Exam reminder"><SelectValue /></SelectTrigger>
          <SelectContent>{[[0, 'Only that morning'], [1, 'The day before'], [2, '2 days before'], [3, '3 days before'], [7, 'A week before']].map(([v, l]) => <SelectItem key={v} value={String(v)}>{l}</SelectItem>)}</SelectContent>
        </Select>
      </Row>
    </Section>
  )
}

export function BackgroundSection({ view, save, run, busy, demo, reload }: {
  view: SettingsView; save: Save; busy: boolean; demo: boolean; reload: () => Promise<void>
  run: (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>
}) {
  const b = view.background
  const toggleStartup = async (on: boolean) => {
    try { const r = await setStartup(on); if (on && !r.ok) toast.error('Could not turn on start with Windows.'); await reload() } catch (e) { toast.error(String((e as Error).message)) }
  }
  const toggleAuto = async () => {
    const r = await run('automation', () => setAutomation(!b.automatic_checks))
    if (r.ok) toast.success(r.message); else toast.error(r.message)
    await reload()
  }
  return (
    <Section id="background" title="Running in the background" description="Windows runs a check each evening and shortly after you sign in, plus an hourly reminder while something is due today. These work even when the app is closed.">
      <Row label="Automatic checks" hint={b.owned_by_installed_app ? 'These tasks belong to the installed app, so they are managed there.' : 'A daily check at 7 PM, one two minutes after sign-in, and the hourly reminder'}>
        <Badge variant="outline" className={b.automatic_checks ? 'border-success/30 bg-success/10 text-success' : 'border-warning/40 bg-warning/10 text-warning'}>{b.automatic_checks ? 'On' : 'Off'}</Badge>
        <Button variant="outline" size="sm" onClick={() => void toggleAuto()} disabled={busy || demo || (b.owned_by_installed_app && b.automatic_checks)}>{b.automatic_checks ? 'Turn off' : 'Turn on'}</Button>
      </Row>
      <SwitchRow label="Start with Windows" hint="Opens the app minimised to the tray when you sign in" checked={b.starts_with_windows} onChange={v => void toggleStartup(v)} disabled={demo} />
      <SwitchRow label="Keep running in the tray when closed" hint="Closing the window leaves the app running; right-click the tray icon to quit" checked={b.close_to_tray} onChange={v => void save({ close_to_tray: v })} />
      <SwitchRow label="Check for app updates" hint="Looks for a newer version now and then" checked={b.check_updates} onChange={v => void save({ check_updates: v })} />
    </Section>
  )
}
