import { useEffect, useRef, useState } from 'react'
import { CircleCheck, FileText, Trash2, Upload } from 'lucide-react'
import { ALLOWED, checkFile, type Assignment } from '@/api'
import { StatusBadge } from '@/components/assignments-table'
import { Alert } from '@/components/inline-alert'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Separator } from '@/components/ui/separator'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { countdown, dueParts, sizeLabel } from '@/format'
import { cn } from '@/lib/utils'
import type { Running } from '@/useEngine'

/** Where an action is, as a bar the student can read: the engine reports steps, not percentages. */
function stepValue(step: string): number {
  const s = step.toLowerCase()
  if (s.includes('sign')) return 18
  if (s.includes('remov')) return 42
  if (s.includes('upload')) return 68
  if (s.includes('check')) return 90
  return 8
}

type Props = {
  a: Assignment | null
  now: number
  demo: boolean
  running: Running | null
  onClose: () => void
  onUpload: (file: File, replace: boolean) => void
  onDelete: () => void
}

export function AssignmentSheet({ a, now, demo, running, onClose, onUpload, onDelete }: Props) {
  return (
    <Sheet open={!!a} onOpenChange={o => { if (!o && !(running && running.assignmentId === a?.id)) onClose() }}>
      <SheetContent className="flex w-full flex-col gap-0 overflow-y-auto sm:max-w-md">
        {a && <Body key={a.id} a={a} now={now} demo={demo} running={running} onUpload={onUpload} onDelete={onDelete} />}
      </SheetContent>
    </Sheet>
  )
}

function Body({ a, now, demo, running, onUpload, onDelete }: Omit<Props, 'onClose' | 'a'> & { a: Assignment }) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [over, setOver] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const due = dueParts(a.due_at)
  const left = countdown(a.due_at, now)
  const mine = running?.assignmentId === a.id
  const otherBusy = !!running && !mine
  const replace = a.can_replace
  const canAct = (a.can_upload || a.can_replace) && !demo

  useEffect(() => {
    const pick = () => { if (canAct && !running) input.current?.click() }
    window.addEventListener('am:pick', pick)
    return () => window.removeEventListener('am:pick', pick)
  }, [canAct, running])

  const choose = (f: File | undefined | null) => {
    if (!f) return
    const bad = checkFile(f)
    setError(bad)
    setFile(bad ? null : f)
  }

  return (
    <>
      <SheetHeader className="gap-2 pr-12">
        <div><StatusBadge a={a} /></div>
        <SheetTitle className="text-xl leading-tight text-balance">{a.title}</SheetTitle>
        <SheetDescription>{a.course} · #{a.assign_no}</SheetDescription>
      </SheetHeader>

      <div className="flex flex-col gap-6 px-4 pb-6">
        <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 text-sm">
          <dt className="text-muted-foreground">Due</dt>
          <dd className="num text-right">{due.day}{due.time && ` · ${due.time}`}</dd>
          {a.open && (<><dt className="text-muted-foreground">Time left</dt><dd className="num text-right">{left.big}</dd></>)}
          {a.is_extended && a.original_due_date && (<><dt className="text-muted-foreground">Extended from</dt><dd className="num text-right">{a.original_due_date}</dd></>)}
          <dt className="text-muted-foreground">Your submission</dt>
          <dd className="text-right">{a.is_submitted ? 'Uploaded' : 'Nothing yet'}</dd>
          {a.marks && !/not marked/i.test(a.marks) && (<><dt className="text-muted-foreground">Marks</dt><dd className="num text-right">{a.marks}</dd></>)}
        </dl>

        <Separator />

        {mine && running ? (
          <div className="flex flex-col gap-3 rounded-lg border p-4" role="status" aria-live="polite">
            <div className="text-sm font-medium">{running.kind === 'delete' ? 'Deleting' : replace ? 'Replacing' : 'Uploading'}</div>
            <Progress value={stepValue(running.step)} />
            <p className="text-muted-foreground text-xs">{running.step.replace(/[….]+$/, '')}. Keep the app open until this finishes.</p>
          </div>
        ) : canAct ? (
          <section className="flex flex-col gap-3">
            <h4 className="text-sm font-medium">{replace ? 'Replace your submission' : 'Upload your work'}</h4>
            {!file ? (
              <>
                <button type="button" disabled={otherBusy} onClick={() => input.current?.click()}
                  onDragOver={e => { e.preventDefault(); setOver(true) }} onDragLeave={() => setOver(false)}
                  onDrop={e => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files[0]) }}
                  className={cn('text-muted-foreground flex flex-col items-center gap-1.5 rounded-lg border border-dashed px-4 py-9 text-center transition-colors hover:bg-muted/50 disabled:opacity-50',
                    over && 'border-brand bg-brand/5 text-foreground')}>
                  <Upload className="text-foreground size-5" />
                  <span className="text-foreground text-sm font-medium">Drop a file here</span>
                  <span className="text-xs">or click to choose · PDF, Word, Excel or zip · up to 15 MB</span>
                </button>
                {error && <Alert tone="warning">{error}</Alert>}
              </>
            ) : (
              <div className="flex flex-col gap-3">
                <div className="flex items-center gap-3 rounded-lg border p-3">
                  <FileText className="text-muted-foreground size-5 shrink-0" />
                  <div className="min-w-0">
                    <div className="truncate text-sm font-medium">{file.name}</div>
                    <div className="text-muted-foreground text-xs">{sizeLabel(file.size)}</div>
                  </div>
                </div>
                {replace && <Alert tone="warning">Your current submission is deleted first, then this file is uploaded. You can do it again until the deadline.</Alert>}
                <div className="flex gap-2">
                  <Button size="lg" disabled={otherBusy} onClick={() => { onUpload(file, replace); setFile(null) }}>
                    <Upload />{replace ? 'Replace and upload' : 'Upload'}
                  </Button>
                  <Button size="lg" variant="ghost" onClick={() => setFile(null)}>Choose another</Button>
                </div>
                <p className="text-muted-foreground text-xs">You are graded on what you upload.</p>
              </div>
            )}
            <input ref={input} type="file" className="sr-only" tabIndex={-1} accept={ALLOWED.join(',')}
              onChange={e => { choose(e.target.files?.[0]); e.target.value = '' }} />
          </section>
        ) : a.is_submitted ? (
          <div className="flex items-center gap-3 rounded-lg border p-3 text-sm">
            <CircleCheck className="text-success size-5" />
            <div><div className="font-medium">Submitted</div><div className="text-muted-foreground text-xs">The portal is no longer accepting changes.</div></div>
          </div>
        ) : (
          <Alert tone="info">{demo ? 'Sample data: connect the engine to upload.' : 'The portal is not accepting a submission for this assignment.'}</Alert>
        )}

        {replace && !mine && !demo && (
          confirmDelete ? (
            <Alert tone="danger">
              <div className="flex flex-col gap-2">
                <span>Delete your submission? You can upload again until the deadline.</span>
                <div className="flex gap-2">
                  <Button size="sm" variant="destructive" disabled={otherBusy} onClick={() => { setConfirmDelete(false); onDelete() }}><Trash2 />Delete</Button>
                  <Button size="sm" variant="ghost" onClick={() => setConfirmDelete(false)}>Keep it</Button>
                </div>
              </div>
            </Alert>
          ) : (
            <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive self-start" disabled={otherBusy} onClick={() => setConfirmDelete(true)}>
              <Trash2 />Delete submission
            </Button>
          )
        )}
      </div>
    </>
  )
}

