import { BookOpen, Building2, CalendarDays, GraduationCap, IdCard, Users } from 'lucide-react'
import type { SettingsView, State } from '@/api'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { ago, initials } from '@/format'
import { Section } from './parts'

/** Who the app is signed in as, read from the portal and the saved account. */
export function ProfileCard({ view, state, now }: { view: SettingsView; state: State; now: number }) {
  const m = state.meta
  // the class most of your courses are in (a lab can sit in another section)
  const counts = new Map<string, number>()
  for (const c of state.attendance.courses) if (c.class) counts.set(c.class, (counts.get(c.class) ?? 0) + 1)
  const cls = [...counts.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
  const rows: { icon: typeof IdCard; label: string; value: string }[] = [
    { icon: IdCard, label: 'Enrollment', value: view.account.enrollment || 'not set' },
    { icon: Building2, label: 'Campus', value: view.account.campus },
    { icon: Users, label: 'Class', value: cls || 'not read yet' },
    { icon: CalendarDays, label: 'Semester', value: m.semester || 'not read yet' },
    { icon: BookOpen, label: 'Courses', value: m.courses?.length ? `${m.courses.length} this semester` : 'none listed' },
    { icon: GraduationCap, label: 'CGPA', value: state.standing ? `${state.standing.cgpa.toFixed(2)} after ${state.standing.semester}` : 'no results yet' },
  ]
  return (
    <Section id="profile-card" title="Your profile" description="What the portal says about you. The app only reads this; it cannot change it.">
      <div className="flex flex-wrap items-center gap-4 pb-4">
        <Avatar className="size-14 rounded-2xl"><AvatarFallback className="rounded-2xl text-base font-semibold">{initials(m.student_name)}</AvatarFallback></Avatar>
        <div className="min-w-0">
          <div className="text-lg font-semibold tracking-tight">{m.student_name || 'Student'}</div>
          <div className="text-muted-foreground text-xs">Last checked {m.last_sync ? ago(m.last_sync, now) : 'never'}</div>
        </div>
      </div>
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {rows.map(r => (
          <div key={r.label} className="flex items-start gap-3 rounded-xl border p-3">
            <r.icon className="text-muted-foreground mt-0.5 size-4 shrink-0" />
            <div className="min-w-0"><dt className="text-muted-foreground text-xs">{r.label}</dt><dd className="truncate text-sm font-medium" title={r.value}>{r.value}</dd></div>
          </div>
        ))}
      </dl>
    </Section>
  )
}
