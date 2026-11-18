import { useEffect, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { AlertTriangle, CheckCircle2, FileText, Trash2, Upload, X } from 'lucide-react'
import { ALLOWED, checkFile, type Assignment } from './api'
import { countdown, dueParts, sizeLabel, toneOf } from './format'
import type { Running } from './useEngine'

type Props = {
  a: Assignment
  now: number
  demo: boolean
  running: Running | null
  onClose: () => void
  onUpload: (file: File, replace: boolean) => void
  onDelete: () => void
}

export function Detail({ a, now, demo, running, onClose, onUpload, onDelete }: Props) {
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')
  const [over, setOver] = useState(false)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const input = useRef<HTMLInputElement>(null)
  const tone = toneOf(a.urgency)
  const due = dueParts(a.due_at)
  const left = countdown(a.due_at, now)
  const mine = running?.assignmentId === a.id
  const otherBusy = !!running && !mine
  const replace = a.can_replace
  const canAct = (a.can_upload || a.can_replace) && !demo

  // the 'u' shortcut asks for the file picker
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
    <motion.aside className="panel" aria-label="Assignment details" initial={{ opacity: 0, x: 28 }} animate={{ opacity: 1, x: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 32 }}>
      <div className="panel-inner">
        <div className="panel-top">
          <span className={`pill tone-${tone}`}>{a.label}</span>
          <button className="icon-btn" onClick={onClose} aria-label="Close details"><X /></button>
        </div>

        <div>
          <h3>{a.title}</h3>
          <div className="meta">{a.course} · #{a.assign_no}</div>
        </div>

        <dl className="facts">
          <dt>Due</dt>
          <dd className="mono">{due.day}{due.time && ` · ${due.time}`}</dd>
          {a.open && (<><dt>Time left</dt><dd className="mono" style={{ color: `var(--${tone === 'later' || tone === 'week' ? 'ink-2' : tone})` }}>{left.big}</dd></>)}
          {a.is_extended && a.original_due_date && (<><dt>Extended from</dt><dd className="mono">{a.original_due_date}</dd></>)}
          <dt>Your submission</dt>
          <dd>{a.is_submitted ? 'Uploaded' : 'Nothing yet'}</dd>
          {a.marks && !/not marked/i.test(a.marks) && (<><dt>Marks</dt><dd className="mono">{a.marks}</dd></>)}
        </dl>

        {mine && running ? (
          <div className="working" role="status" aria-live="polite">
            <b>{running.kind === 'delete' ? 'Deleting…' : replace ? 'Replacing…' : 'Uploading…'}</b>
            <div className="progress" />
            <span>{running.step.replace(/[….]+$/, '')}. Keep the app open until this finishes.</span>
          </div>
        ) : canAct ? (
          <section>
            <h4 className="section-title">{replace ? 'Replace your submission' : 'Upload your work'}</h4>
            {!file ? (
              <>
                <button
                  className="drop" data-over={over} disabled={otherBusy}
                  onClick={() => input.current?.click()}
                  onDragOver={e => { e.preventDefault(); setOver(true) }}
                  onDragLeave={() => setOver(false)}
                  onDrop={e => { e.preventDefault(); setOver(false); choose(e.dataTransfer.files[0]) }}
                >
                  <Upload aria-hidden />
                  <b>Drop a file here</b>
                  <small>or click to choose · PDF, Word, Excel or zip · up to 15 MB</small>
                </button>
                {error && <div className="notice" role="alert" style={{ marginTop: 12 }}><AlertTriangle aria-hidden /><span>{error}</span></div>}
              </>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                <div className="file-card">
                  <FileText aria-hidden />
                  <div style={{ minWidth: 0 }}><b>{file.name}</b><span>{sizeLabel(file.size)}</span></div>
                </div>
                {replace && (
                  <div className="notice"><AlertTriangle aria-hidden /><span>Your current submission is deleted first, then this file is uploaded. You can do it again until the deadline.</span></div>
                )}
                <div className="row-actions">
                  <button className="btn btn-primary btn-lg" disabled={otherBusy} onClick={() => { onUpload(file, replace); setFile(null) }}>
                    <Upload aria-hidden />{replace ? 'Replace and upload' : 'Upload'}
                  </button>
                  <button className="btn btn-ghost btn-lg" onClick={() => setFile(null)}>Choose another</button>
                </div>
                <small style={{ color: 'var(--muted)' }}>You are graded on what you upload.</small>
              </div>
            )}
            <input ref={input} type="file" className="sr" tabIndex={-1} accept={ALLOWED.join(',')}
              onChange={e => { choose(e.target.files?.[0]); e.target.value = '' }} />
          </section>
        ) : a.is_submitted ? (
          <div className="file-card"><CheckCircle2 aria-hidden style={{ color: 'var(--ok)' }} /><div><b>Submitted</b><span>The portal is no longer accepting changes.</span></div></div>
        ) : (
          <div className="notice"><AlertTriangle aria-hidden /><span>{demo ? 'Sample data: connect the engine to upload.' : 'The portal is not accepting a submission for this assignment.'}</span></div>
        )}

        {replace && !mine && !demo && (
          confirmDelete ? (
            <div className="notice" role="alertdialog">
              <AlertTriangle aria-hidden />
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                <span>Delete your submission? You can upload again until the deadline.</span>
                <div className="row-actions">
                  <button className="btn btn-danger" disabled={otherBusy} onClick={() => { setConfirmDelete(false); onDelete() }}><Trash2 aria-hidden />Delete</button>
                  <button className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>Keep it</button>
                </div>
              </div>
            </div>
          ) : (
            <button className="btn btn-ghost btn-danger" style={{ alignSelf: 'flex-start' }} onClick={() => setConfirmDelete(true)} disabled={otherBusy}>
              <Trash2 aria-hidden />Delete submission
            </button>
          )
        )}
      </div>
    </motion.aside>
  )
}
