import { describe, expect, it } from 'vitest'
import { boxWithin, directionBetween } from './slide'

const el = (left: number, top: number, width: number, height: number, scrollLeft = 0, scrollTop = 0) =>
  ({ getBoundingClientRect: () => ({ left, top, width, height }) as DOMRect, scrollLeft, scrollTop })

describe('directionBetween', () => {
  const order = ['home', 'assignments', 'attendance', 'settings']
  it('is 1 going down the list and -1 going up', () => {
    expect(directionBetween(order, 'home', 'attendance')).toBe(1)
    expect(directionBetween(order, 'settings', 'assignments')).toBe(-1)
  })
  it('is 0 for the same page, a first page or an unknown page', () => {
    expect(directionBetween(order, 'home', 'home')).toBe(0)
    expect(directionBetween(order, null, 'home')).toBe(0)
    expect(directionBetween(order, 'home', 'notfound')).toBe(0)
    expect(directionBetween(order, 'notfound', 'home')).toBe(0)
  })
})

describe('boxWithin', () => {
  it('measures the item inside its host', () => {
    expect(boxWithin(el(100, 50, 300, 400), el(110, 90, 200, 32))).toEqual({ x: 10, y: 40, w: 200, h: 32 })
  })
  it('follows the host scroll, so the marker scrolls with the list', () => {
    expect(boxWithin(el(0, 0, 300, 200, 0, 120), el(0, -100, 200, 32))).toEqual({ x: 0, y: 20, w: 200, h: 32 })
    expect(boxWithin(el(0, 0, 300, 40, 75, 0), el(-60, 0, 90, 32))).toEqual({ x: 15, y: 0, w: 90, h: 32 })
  })
})
