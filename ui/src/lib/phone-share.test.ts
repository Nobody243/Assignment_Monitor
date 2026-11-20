import { describe, expect, it } from 'vitest'
import { agoText, phoneShareLine } from './phone-share'
import type { PhoneShareStatus } from '@/api'

const base: PhoneShareStatus = { available: true, enabled: true, covered_by_cloud: false, login: 'alex', repo: 'alex/assignment-monitor-cloud', last: null, error: null }
const now = Date.parse('2026-11-20T12:00:00')

describe('phone share wording', () => {
  it('says how long ago in plain units', () => {
    expect(agoText('2026-11-20T11:59:40', now)).toBe('just now')
    expect(agoText('2026-11-20T11:30:00', now)).toBe('30 min ago')
    expect(agoText('2026-11-20T08:00:00', now)).toBe('4 h ago')
    expect(agoText('2026-11-15T12:00:00', now)).toBe('5 days ago')
    expect(agoText('not a date', now)).toBe('')
  })
  it('explains each state', () => {
    expect(phoneShareLine({ ...base, enabled: false }, now).label).toMatch(/^Off/)
    expect(phoneShareLine({ ...base, covered_by_cloud: true }, now).label).toContain('through Cloud checks')
    expect(phoneShareLine({ ...base, last: '2026-11-20T11:30:00' }, now).hint).toContain('30 min ago')
    expect(phoneShareLine({ ...base, error: 'GitHub answered 502' }, now).hint).toContain('failed: GitHub answered 502')
    expect(phoneShareLine(base, now).hint).toContain('Nothing sent yet')
  })
})
