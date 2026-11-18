import { beforeEach, describe, expect, it } from 'vitest'
import { activitySnapshot, clearActivity, record } from '@/lib/activity'
import { PAGES, PAGE_TITLES, SETTINGS_TABS, parseRoute } from '@/lib/router'

describe('routing: every known page, and a real 404 for the rest', () => {
  it('an empty hash is Home', () => {
    expect(parseRoute('')).toEqual({ page: 'home', sub: null, missing: '' })
    expect(parseRoute('#/')).toEqual({ page: 'home', sub: null, missing: '' })
  })
  it('knows every page', () => {
    for (const p of PAGES) expect(parseRoute(`#/${p}`).page).toBe(p)
    expect(parseRoute('#/settings/').page).toBe('settings')       // a trailing slash is fine
  })
  it('settings has tabs, and an old #/activity link lands on the Activity tab', () => {
    expect(parseRoute('#/settings')).toEqual({ page: 'settings', sub: null, missing: '' })
    for (const t of SETTINGS_TABS) expect(parseRoute(`#/settings/${t.key}`)).toEqual({ page: 'settings', sub: t.key, missing: '' })
    expect(parseRoute('#/activity')).toEqual({ page: 'settings', sub: 'activity', missing: '' })
    expect(parseRoute('#/settings/nope').page).toBe('notfound')
    expect(parseRoute('#/home/profile').page).toBe('notfound')       // only settings has sub-pages
  })
  it('every settings tab is distinct and named', () => {
    expect(new Set(SETTINGS_TABS.map(t => t.key)).size).toBe(SETTINGS_TABS.length)
    for (const t of SETTINGS_TABS) expect(t.label.length).toBeGreaterThan(2)
  })
  it('unknown pages are a 404 that remembers what was asked for', () => {
    expect(parseRoute('#/nope')).toEqual({ page: 'notfound', sub: null, missing: 'nope' })
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
