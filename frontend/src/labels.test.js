import { describe, expect, it } from 'vitest'

import { facilityText, violationTypeLabel, zoneLabel } from './labels.js'

describe('zoneLabel', () => {
  it('translates known zones and keeps unknown values', () => {
    expect(zoneLabel('quiet')).toBe('静音区')
    expect(zoneLabel('exam_prep')).toBe('考研区')
    expect(zoneLabel('rooftop')).toBe('rooftop')
    expect(zoneLabel('')).toBe('—')
    expect(zoneLabel(null)).toBe('—')
  })
})

describe('violationTypeLabel', () => {
  it('accepts either case and falls back to the raw value', () => {
    expect(violationTypeLabel('NO_SHOW')).toBe('预约未到（爽约）')
    expect(violationTypeLabel('temp_leave_timeout')).toBe('暂离超时未归')
    expect(violationTypeLabel('other')).toBe('other')
    expect(violationTypeLabel('')).toBe('—')
  })
})

describe('facilityText', () => {
  it('joins the facilities a seat actually has', () => {
    expect(facilityText(null)).toBe('—')
    expect(facilityText({})).toBe('—')
    expect(facilityText({ has_power: true, by_window: true, accessible: false })).toBe('电源、靠窗')
    expect(facilityText({ accessible: true })).toBe('无障碍')
  })
})
