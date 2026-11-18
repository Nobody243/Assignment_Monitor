import { useMemo, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import type { Results } from '@/api'
import { PageHeader, Stat } from '@/components/page-header'
import { Alert } from '@/components/inline-alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { GRADES, gpaOf, project, totals } from '@/lib/results'
import { cn } from '@/lib/utils'

const gradeTone = (g: string) => (!g ? 'text-muted-foreground' : g.startsWith('A') ? 'border-success/30 bg-success/10 text-success' : g.startsWith('B') ? 'border-brand/30 bg-brand/10 text-brand' : g.startsWith('C') ? 'border-warning/40 bg-warning/10 text-warning' : 'border-destructive/30 bg-destructive/10 text-destructive')
const f2 = (n: number | null | undefined) => (n == null ? '–' : n.toFixed(2))
const shortName = (n: string) => n.replace(/^(Fall|Spring|Summer)-(\d{2})(\d{2})$/, (_m, t: string, _c: string, y: string) => `${t[0]}${y}`)

export function ResultsPage({ results }: { results: Results }) {
  const semesters = results?.semesters ?? []
  const current = [...semesters].reverse().find(s => !s.complete)
  const [selName, setSel] = useState<string | null>(null)
  const sel = semesters.find(s => s.name === selName) ?? current ?? semesters[semesters.length - 1]
  const [picks, setPicks] = useState<Record<string, string>>({})
  const done = useMemo(() => totals(semesters.filter(s => s.complete)), [semesters])
  const proj = useMemo(() => project(semesters, picks), [semesters, picks])
  const scenarios = useMemo(() => (current ? ['A', 'A-', 'B+', 'B', 'B-', 'C+', 'C'].map(g => ({ g, ...project(semesters, Object.fromEntries(current.courses.map(c => [c.code, g]))) })) : []), [semesters, current])
  const series = semesters.filter(s => s.complete && s.gpa != null)

  if (!semesters.length) {
    return (
      <div className="flex flex-col gap-5">
        <PageHeader title="Results" />
        <Empty className="border border-dashed"><EmptyHeader><EmptyTitle>No results read yet</EmptyTitle><EmptyDescription>Run a check, with Results switched on, to read your transcript from the CMS.</EmptyDescription></EmptyHeader></Empty>
      </div>
    )
  }

  const isCurrent = !!sel && !sel.complete
  const semGpa = sel ? (sel.gpa ?? gpaOf(sel.courses)) : null

  return (
    <div className="flex flex-col gap-5">
      <PageHeader title="Results" description="Your transcript one semester at a time, read from the CMS. Nothing here changes the portal." />
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Stat label="CGPA" value={f2(done.cgpa)} sub={`over ${semesters.filter(s => s.complete).length} semesters`} />
        <Stat label="Last semester GPA" value={f2(series[series.length - 1]?.gpa)} sub={series[series.length - 1]?.name} />
        <Stat label="Credits earned" value={done.earned} sub={`of ${done.credits} attempted`} />
        <Stat label="Running semester" value={current ? current.name : '–'} sub={current ? `${current.courses.length} courses awaiting grades` : 'all graded'} />
      </div>

      <section className="bg-card panel-lift rounded-2xl border p-5" aria-label="GPA by semester">
        <div className="mb-4 flex items-center justify-between"><h2 className="text-sm font-semibold">GPA and CGPA by semester</h2><span className="text-muted-foreground text-xs">GPA bars, CGPA beneath</span></div>
        <div className="flex h-36 items-end gap-3">
          {series.map(s => (
            <button key={s.name} type="button" onClick={() => setSel(s.name)} className="group flex h-full min-w-0 flex-1 flex-col items-center justify-end gap-1.5" title={`${s.name}: GPA ${f2(s.gpa)}, CGPA ${f2(s.cgpa)}`}>
              <span className="num text-xs">{f2(s.gpa)}</span>
              <div className={cn('w-full max-w-20 rounded-lg transition-colors', sel?.name === s.name ? 'bg-primary' : 'bg-banner/70 group-hover:bg-banner dark:bg-foreground/50 dark:group-hover:bg-foreground/70')} style={{ height: `${Math.max(8, ((s.gpa ?? 0) / 4) * 78)}%` }} />
              <span className="text-muted-foreground text-[11px]">{shortName(s.name)}</span>
              <span className="num text-muted-foreground text-[10px]">{f2(s.cgpa)}</span>
            </button>
          ))}
        </div>
      </section>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex max-w-full gap-1 overflow-x-auto pb-1" role="tablist" aria-label="Semester">
          {semesters.map(s => (
            <button key={s.name} role="tab" aria-selected={sel?.name === s.name} onClick={() => setSel(s.name)}
              className={cn('shrink-0 rounded-lg border px-3 py-1.5 text-sm transition-colors', sel?.name === s.name ? 'bg-primary text-primary-foreground border-transparent font-medium' : 'text-muted-foreground hover:bg-muted')}>
              {s.name}{!s.complete && <span className="ml-1.5 text-xs opacity-80">running</span>}
            </button>
          ))}
        </div>
        {isCurrent && Object.keys(picks).length > 0 && <Button variant="ghost" size="sm" onClick={() => setPicks({})}><RotateCcw />Reset what-ifs</Button>}
      </div>

      {sel && (
        <div className="bg-card panel-lift overflow-hidden rounded-2xl border">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
            <div><h2 className="font-semibold">{sel.name}</h2><p className="text-muted-foreground text-xs">{isCurrent ? 'Grades are not posted yet. Pick a grade per course to see where you would land.' : 'Posted by the portal.'}</p></div>
            <div className="flex gap-6 text-right">
              <div><div className="text-muted-foreground text-xs">{isCurrent ? 'Projected GPA' : 'GPA'}</div><div className="num text-xl font-medium">{f2(isCurrent ? proj.gpa : semGpa)}</div></div>
              <div><div className="text-muted-foreground text-xs">{isCurrent ? 'Projected CGPA' : 'CGPA'}</div><div className="num text-xl font-medium">{f2(isCurrent ? proj.cgpa : sel.cgpa)}</div></div>
            </div>
          </div>
          <Table>
            <TableHeader className="bg-muted/40"><TableRow className="hover:bg-transparent">
              <TableHead className="pl-5">Course</TableHead><TableHead className="w-20 text-right">Credits</TableHead>
              <TableHead className="w-36">{isCurrent ? 'What if…' : 'Grade'}</TableHead><TableHead className="w-24 text-right">Points</TableHead>
            </TableRow></TableHeader>
            <TableBody>
              {sel.courses.map(c => (
                <TableRow key={c.code}>
                  <TableCell className="pl-5"><div className="font-medium">{c.title}</div><div className="num text-muted-foreground text-xs">{c.code}</div></TableCell>
                  <TableCell className="num text-right">{c.credits}</TableCell>
                  <TableCell>
                    {isCurrent ? (
                      <Select value={picks[c.code] ?? 'none'} onValueChange={v => setPicks(p => { const n = { ...p }; if (v === 'none') delete n[c.code]; else n[c.code] = v; return n })}>
                        <SelectTrigger size="sm" className="w-28" aria-label={`Grade for ${c.title}`}><SelectValue /></SelectTrigger>
                        <SelectContent><SelectItem value="none">No grade</SelectItem>{GRADES.map(g => <SelectItem key={g} value={g}>{g}</SelectItem>)}</SelectContent>
                      </Select>
                    ) : c.grade ? <Badge variant="outline" className={gradeTone(c.grade)}>{c.grade}</Badge> : <span className="text-muted-foreground text-sm">–</span>}
                  </TableCell>
                  <TableCell className="num text-muted-foreground text-right">{isCurrent ? (picks[c.code] ? 'what-if' : '–') : f2(c.points)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {isCurrent && scenarios.length > 0 && (
        <section className="bg-card panel-lift rounded-2xl border p-5" aria-label="Same grade in every course">
          <h2 className="text-sm font-semibold">If every course ended on the same grade</h2>
          <p className="text-muted-foreground mt-0.5 mb-4 text-xs">Where your CGPA would land, from {f2(done.cgpa)} today.</p>
          <div className="grid grid-cols-4 gap-2 sm:grid-cols-7">
            {scenarios.map(s => (
              <div key={s.g} className="rounded-xl border p-2.5 text-center">
                <div className="text-sm font-medium">{s.g}</div>
                <div className="num mt-1 text-base">{f2(s.cgpa)}</div>
                <div className={cn('num text-[11px]', (s.cgpa ?? 0) >= (done.cgpa ?? 0) ? 'text-success' : 'text-destructive')}>{s.cgpa != null && done.cgpa != null ? `${s.cgpa >= done.cgpa ? '+' : ''}${(s.cgpa - done.cgpa).toFixed(2)}` : ''}</div>
              </div>
            ))}
          </div>
        </section>
      )}
      <Alert tone="info">Figures use the portal's own grade scale and cumulative formula, checked against a real transcript. What-ifs are never saved.</Alert>
    </div>
  )
}
