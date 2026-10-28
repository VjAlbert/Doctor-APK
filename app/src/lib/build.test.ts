import { describe, expect, it } from 'vitest'
import { buildsDiffer, isOlderReport } from './build'

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
