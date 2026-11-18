import { ChevronRight, CircleCheck } from 'lucide-react'
import type { Assignment } from '@/api'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { dueParts } from '@/format'
import { cn } from '@/lib/utils'

export function StatusBadge({ a }: { a: Assignment }) {
  if (a.is_submitted) return <Badge variant="outline" className="border-success/30 bg-success/10 text-success gap-1"><CircleCheck className="size-3" />Submitted</Badge>
  if (a.urgency === 'missed') return <Badge variant="outline" className="border-destructive/30 bg-destructive/10 text-destructive">Overdue</Badge>
  if (a.urgency === 'today') return <Badge variant="outline" className="border-destructive/30 bg-destructive/10 text-destructive">{a.label}</Badge>
  if (a.urgency === 'soon') return <Badge variant="outline" className="border-warning/40 bg-warning/10 text-warning">{a.label}</Badge>
  return <Badge variant="outline" className="text-muted-foreground font-normal">{a.label}</Badge>
}

export function AssignmentsTable({ rows, selectedId, onSelect }: { rows: Assignment[]; selectedId: string | null; onSelect: (id: string) => void }) {
  return (
    <div className="overflow-hidden rounded-lg border">
      <Table>
        <TableHeader className="bg-muted/40">
          <TableRow className="hover:bg-transparent">
            <TableHead className="pl-4">Assignment</TableHead>
            <TableHead className="hidden w-44 sm:table-cell">Due</TableHead>
            <TableHead className="w-40">Status</TableHead>
            <TableHead className="w-28 text-right" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map(a => {
            const d = dueParts(a.due_at)
            return (
              <TableRow key={a.id} data-state={a.id === selectedId ? 'selected' : undefined} tabIndex={0} id={`row-${a.id}`}
                className="group cursor-pointer" onClick={() => onSelect(a.id)}
                onKeyDown={e => { if (e.key === 'Enter') onSelect(a.id) }}>
                <TableCell className="max-w-0 pl-4">
                  <div className="truncate font-medium">{a.title}</div>
                  <div className="text-muted-foreground truncate text-xs">{a.course} · #{a.assign_no}</div>
                </TableCell>
                <TableCell className="hidden sm:table-cell">
                  <span className="num text-sm">{d.day}</span>
                  {d.time && <span className="num text-muted-foreground ml-2 text-xs">{d.time}</span>}
                </TableCell>
                <TableCell><StatusBadge a={a} /></TableCell>
                <TableCell className="text-right">
                  <div className="flex items-center justify-end gap-1">
                    {(a.can_upload || a.can_replace) && (
                      <Button size="sm" variant="outline" tabIndex={-1} className={cn('h-7 opacity-0 transition-opacity group-hover:opacity-100 group-data-[state=selected]:opacity-100 max-sm:opacity-100')}>
                        {a.can_replace ? 'Replace' : 'Upload'}
                      </Button>
                    )}
                    <ChevronRight className="text-muted-foreground size-4" />
                  </div>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}
