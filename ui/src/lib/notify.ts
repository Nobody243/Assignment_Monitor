import { toast as base } from 'sonner'
import { record } from '@/lib/activity'

type Opts = Parameters<typeof base.success>[1]
const detail = (o?: Opts) => (typeof o?.description === 'string' ? o.description : undefined)

/** sonner's toast, with every success and error also written to the activity log. A failure stays on screen longer. */
export const toast = Object.assign((...a: Parameters<typeof base>) => base(...a), {
  success: (message: string, o?: Opts) => { record({ ok: true, title: message, detail: detail(o) }); return base.success(message, o) },
  error: (message: string, o?: Opts) => { record({ ok: false, title: message, detail: detail(o) }); return base.error(message, { duration: 9000, ...o }) },
  info: base.info,
  loading: base.loading,
  dismiss: base.dismiss,
})
