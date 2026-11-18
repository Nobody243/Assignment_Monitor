import { useEffect, useMemo, useRef, useState } from 'react'
import { motion } from 'motion/react'
import { ArrowRight, Moon, RefreshCw, Search } from './icons'
import type { Assignment } from './api'
import { dueParts } from './format'

export type Command = { id: string; label: string; hint?: string; icon: 'sync' | 'theme' | 'go'; run: () => void }

export function Palette({ assignments, commands, onPick, onClose }: {
  assignments: Assignment[]; commands: Command[]; onPick: (id: string) => void; onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [i, setI] = useState(0)
  const list = useRef<HTMLUListElement>(null)

  const items = useMemo(() => {
    const t = q.trim().toLowerCase()
    const cmds = commands.filter(c => !t || c.label.toLowerCase().includes(t))
    const as = assignments
      .filter(a => !t || `${a.title} ${a.course}`.toLowerCase().includes(t))
      .slice(0, 8)
      .map(a => ({ id: a.id, label: a.title, hint: `${a.course} · ${dueParts(a.due_at).day}`, icon: 'go' as const, run: () => onPick(a.id) }))
    return [...cmds, ...as]
  }, [q, assignments, commands, onPick])

  useEffect(() => setI(0), [q])
  useEffect(() => { list.current?.querySelector('[aria-selected="true"]')?.scrollIntoView({ block: 'nearest' }) }, [i])

  const pick = (k: number) => { const it = items[k]; if (it) { onClose(); it.run() } }
  const icon = { sync: <RefreshCw />, theme: <Moon />, go: <ArrowRight /> }

  return (
    <motion.div className="scrim" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.12 }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <motion.div className="palette" role="dialog" aria-label="Search and commands" initial={{ opacity: 0, y: -8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: -6 }} transition={{ type: 'spring', stiffness: 420, damping: 34 }}>
        <div style={{ position: 'relative' }}>
          <Search aria-hidden style={{ position: 'absolute', left: 20, top: 18, width: 16, height: 16, color: 'var(--muted)' }} />
          <input autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder="Search assignments or type a command" aria-label="Search"
            style={{ paddingLeft: 46 }}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setI(v => Math.min(items.length - 1, v + 1)) }
              else if (e.key === 'ArrowUp') { e.preventDefault(); setI(v => Math.max(0, v - 1)) }
              else if (e.key === 'Enter') { e.preventDefault(); pick(i) }
              else if (e.key === 'Escape') onClose()
            }} />
        </div>
        {items.length ? (
          <ul ref={list} role="listbox">
            {items.map((it, k) => (
              <li key={it.id}>
                <button role="option" aria-selected={k === i} onMouseMove={() => setI(k)} onClick={() => pick(k)}>
                  {icon[it.icon]}<span>{it.label}</span>{it.hint && <small>{it.hint}</small>}
                </button>
              </li>
            ))}
          </ul>
        ) : <div className="none">Nothing matches “{q}”.</div>}
      </motion.div>
    </motion.div>
  )
}
