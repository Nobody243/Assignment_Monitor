import { beforeEach, describe, expect, it } from 'vitest'
import { activitySnapshot, clearActivity, record } from '@/lib/activity'
import { PAGES, PAGE_TITLES, parseRoute } from '@/lib/router'

describe('routing: every known page, and a real 404 for the rest', () => {
  it('an empty hash is Home', () => {
    expect(parseRoute('')).toEqual({ page: 'home', missing: '' })
    expect(parseRoute('#/')).toEqual({ page: 'home', missing: '' })
  })
  it('knows every page', () => {
    for (const p of PAGES) expect(parseRoute(`#/${p}`).page).toBe(p)
    expect(parseRoute('#/settings/').page).toBe('settings')       // a trailing slash is fine
  })
  it('unknown pages are a 404 that remembers what was asked for', () => {
    expect(parseRoute('#/nope')).toEqual({ page: 'notfound', missing: 'nope' })
    expect(parseRoute('#/assignments/42').page).toBe('notfound')
  })
  it('a very long path is cut, not echoed whole', () => expect(parseRoute('#/' + 'x'.repeat(500)).missing.length).toBe(80))
  it('every page has a title', () => { for (const p of [...PAGES, 'notfound' as const]) expect(PAGE_TITLES[p]).toBeTruthy() })
})

describe('activity: every outcome is kept', () => {
  beforeEach(() => clearActivity())
  it('records newest first, with its result', () => {
    record({ ok: true, title: 'First' })
    record({ ok: false, title: 'Second', detail: 'it failed' })
    const e = activitySnapshot()
    expect(e.map(x => x.title)).toEqual(['Second', 'First'])
    expect(e[0]).toMatchObject({ ok: false, detail: 'it failed' })
    expect(e[0].id).not.toBe(e[1].id)
  })
  it('keeps only the most recent 200', () => {
    for (let i = 0; i < 230; i++) record({ ok: true, title: `n${i}` })
    expect(activitySnapshot()).toHaveLength(200)
    expect(activitySnapshot()[0].title).toBe('n229')
  })
  it('can be cleared', () => { record({ ok: true, title: 'x' }); clearActivity(); expect(activitySnapshot()).toEqual([]) })
})
