import { describe, expect, it, vi } from 'vitest'
import { buildsDiffer, getEngineInfo, isOlderReport } from './build'

describe('an engine that predates build identifiers', () => {
  it('is reported as unknown, never as "undefined", and counts as a mismatch', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.resolve(new Response(JSON.stringify({ ok: true, categories: [] }), { status: 200 }))))
    const info = await getEngineInfo()
    expect(info).toEqual({ version: 'unknown', build: 'unknown' })
    expect(buildsDiffer('f7920b1', info.build)).toBe(true)
    vi.unstubAllGlobals()
  })
})

describe('build identifiers', () => {
  it('flags a mixed installation only when both builds are real and different', () => {
    expect(buildsDiffer('abc1234', 'abc1234')).toBe(false)
    expect(buildsDiffer('abc1234', 'def5678')).toBe(true)
    expect(buildsDiffer('dev', 'def5678')).toBe(false)   // a development run is not a mixed installation
    expect(buildsDiffer('abc1234', undefined)).toBe(false)
  })

  it('recognises reports saved by an older engine', () => {
    const current = { version: '0.1.0', build: 'f8bee1e' }
    expect(isOlderReport({ engine: { build: 'f8bee1e' } }, current)).toBe(false)
    expect(isOlderReport({ engine: { build: '41b08d7' } }, current)).toBe(true)
    expect(isOlderReport({}, current)).toBe(true)          // reports from before builds were recorded
    expect(isOlderReport({}, null)).toBe(false)            // unknown current engine: say nothing
  })
})
