import { useState } from 'react'
import { ClipboardCopy, Download, ExternalLink } from 'lucide-react'
import { getSupport, getUpdate, installUpdate, type SettingsView, type UpdateInfo } from '@/api'
import { Alert } from '@/components/inline-alert'
import { ConfirmDialog, LoadingButton } from '@/components/feedback'
import { toast } from '@/lib/notify'
import type { Outcome } from '@/useEngine'
import { Button } from '@/components/ui/button'
import { Row, Section } from './parts'

export function AboutSection({ view, version, demo, run, busy: running }: {
  view: SettingsView | null; version: string; demo: boolean; busy: boolean
  run: (kind: string, begin: () => Promise<{ job: string }>) => Promise<Outcome>
}) {
  const [confirm, setConfirm] = useState(false)
  const [info, setInfo] = useState<UpdateInfo | null>(null)
  const [busy, setBusy] = useState(false)
  const about = view?.about
  const check = async () => {
    setBusy(true)
    try { setInfo(await getUpdate()) } catch (e) { setInfo({ error: e instanceof Error ? e.message : 'Could not check.' }) }
    setBusy(false)
  }
  const install = async () => {
    const r = await run('update', installUpdate)
    if (r.ok) toast.success(r.message); else toast.error(r.message)
  }
  const installed = !!about?.installed
  const copySupport = async () => {
    try {
      await navigator.clipboard.writeText((await getSupport()).text)
      toast.success('Copied. Paste it into your bug report: names, emails, enrollment numbers and tokens are already removed.')
    } catch (e) { toast.error('Could not copy the support info', { description: e instanceof Error ? e.message : undefined }) }
  }
  const repo = about?.repo ?? 'https://github.com/Nobody243/Assignment_Monitor'
  const links: [string, string][] = [['What\'s new', `${repo}/blob/main/CHANGELOG.md`], ['Privacy and terms', `${repo}/blob/main/PRIVACY.md`],
    ['Security', `${repo}/blob/main/SECURITY.md`], ['Licenses', `${repo}/blob/main/THIRD_PARTY_LICENSES.md`], ['Source on GitHub', repo], ...(about ? [['Website', about.site] as [string, string]] : [])]
  return (
    <Section id="about" title="About" description={about ? `Assignment Monitor ${about.version} ${about.tagline}` : `Assignment Monitor ${version}`}>
      <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2 pb-3 text-sm">
        <dt className="text-muted-foreground">Version</dt><dd className="num text-right">{about?.version ?? version}</dd>
        <dt className="text-muted-foreground">Build</dt><dd className="text-right">{about ? (about.installed ? 'installed build' : 'running from source') : 'unknown'}</dd>
        <dt className="text-muted-foreground">Made by</dt><dd className="text-right">{about?.author ?? 'Nobody243'}</dd>
        <dt className="text-muted-foreground">Licence</dt><dd className="text-right">{about?.license ?? 'MIT'}</dd>
        <dt className="text-muted-foreground">Interface</dt><dd className="text-right">new interface (prototype)</dd>
        <dt className="text-muted-foreground">Data</dt><dd className="text-right">{demo ? 'sample data (engine not running)' : 'live, from the app engine'}</dd>
      </dl>
      <Row label="Updates" hint={info ? (info.error ?? (info.newer ? `Version ${info.version} is available.` : `You have the latest version (${info.current ?? version}).`)) : 'Ask GitHub whether a newer version exists'}>
        <LoadingButton variant="outline" size="sm" loading={busy} disabled={demo} onClick={() => void check()}>Check for updates</LoadingButton>
        {info?.newer && installed && <Button size="sm" disabled={running || demo} onClick={() => setConfirm(true)}><Download />Install {info.version}</Button>}
        {info?.newer && info.page && !installed && <Button size="sm" asChild><a href={info.page} target="_blank" rel="noreferrer"><ExternalLink />Get {info.version}</a></Button>}
      </Row>
      <ConfirmDialog open={confirm} onOpenChange={setConfirm} title={`Install version ${info?.version ?? ''}?`}
        description="The app downloads the update, checks it against the checksum published with the release, then closes and reopens by itself. Your data and settings are kept."
        yes="Yes, install" no="Not now" onYes={() => void install()} />
      <Row label="Support info" hint="The version, which features are on and the recent log, with personal details removed, ready to paste into a bug report">
        <Button variant="outline" size="sm" disabled={demo} onClick={() => void copySupport()}><ClipboardCopy />Copy support info</Button>
        <Button variant="ghost" size="sm" asChild><a href={`${repo}/issues/new`} target="_blank" rel="noreferrer">Report a problem<ExternalLink className="size-3" /></a></Button>
      </Row>
      <Row label="Setup walkthrough" hint="Go through the first-run steps again: sign in, look, reminders, automatic checks, files">
        <Button variant="outline" size="sm" disabled={demo} onClick={() => window.dispatchEvent(new Event('am:setup'))}>Run setup again</Button>
      </Row>
      <div className="flex flex-wrap gap-2 pt-3">
        {links.map(([label, href]) => <Button key={label} variant="outline" size="sm" asChild><a href={href} target="_blank" rel="noreferrer">{label}<ExternalLink className="size-3" /></a></Button>)}
      </div>
      <div className="mt-4"><Alert tone="info">Unofficial app. Not affiliated with, endorsed by, or supported by Bahria University.</Alert></div>
    </Section>
  )
}
