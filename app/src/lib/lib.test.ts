import { describe, expect, it } from 'vitest'
import { formatParam, formatSize, shortHash, timeAgo } from './format'
import { countBySeverity, filterFindings, groupBySeverity, visibleByDefault } from './findings'
import { addToHistory, clearHistory, loadHistory, MAX_ENTRIES, type KeyValueStore } from './history'
import { createNdjsonParser } from './ndjson'
import { detectLang, missingTranslations } from './ui'
import type { Finding, Report, Severity } from './types'

const finding = (id: string, severity: Severity): Finding => ({
  id, severity, module: 'm', params: {}, text: { title: id, description: '', advice: '' },
})

const report = (sha: string): Report => ({
  file: { name: `${sha}.apk`, size: 1, kind: 'apk', md5: '', sha1: '', sha256: sha },
  app: { package: 'p', name: null, version_name: null, version_code: null, min_sdk: null, target_sdk: null },
  certificates: [], permissions: [], iocs: {}, stats: {},
  authenticity: { status: 'unknown', label: '', sources: [], expected: [] },
  reputation: { status: 'disabled' },
  category: { id: 'unknown', source: 'auto', confidence: 'none' },
  verdict: { id: 'caution', level: 'medium', score: 30, counts: { critical: 0, high: 0, medium: 0, low: 0, info: 0 },
    reasons: [], text: { title: '', summary: '', limitations: '', category: '' } },
  findings: [],
})

function memoryStore(): KeyValueStore & { data: Map<string, string> } {
  const data = new Map<string, string>()
  return { data, getItem: (k) => data.get(k) ?? null, setItem: (k, v) => void data.set(k, v), removeItem: (k) => void data.delete(k) }
}

describe('ndjson parser', () => {
  const encode = (s: string) => new TextEncoder().encode(s)

  it('emits one value per line even when chunks split lines', () => {
    const seen: unknown[] = []
    const parser = createNdjsonParser((v) => seen.push(v))
    parser.push(encode('{"a":1}\n{"b"'))
    parser.push(encode(':2}\n'))
    parser.end()
    expect(seen).toEqual([{ a: 1 }, { b: 2 }])
  })

  it('handles a last line without a trailing newline and blank lines', () => {
    const seen: unknown[] = []
    const parser = createNdjsonParser((v) => seen.push(v))
    parser.push(encode('\n{"a":1}\n\n{"z":9}'))
    parser.end()
    expect(seen).toEqual([{ a: 1 }, { z: 9 }])
  })

  it('does not break multibyte characters split across chunks', () => {
    const bytes = encode('{"t":"è"}\n')
    const seen: unknown[] = []
    const parser = createNdjsonParser((v) => seen.push(v))
    parser.push(bytes.slice(0, 7))
    parser.push(bytes.slice(7))
    parser.end()
    expect(seen).toEqual([{ t: 'è' }])
  })
})

describe('findings helpers', () => {
  const all = [finding('a', 'low'), finding('b', 'critical'), finding('c', 'info'), finding('d', 'low')]

  it('counts, filters and groups by severity', () => {
    expect(countBySeverity(all)).toEqual({ critical: 1, high: 0, medium: 0, low: 2, info: 1 })
    expect(filterFindings(all, 'low').map((f) => f.id)).toEqual(['a', 'd'])
    expect(filterFindings(all, 'all')).toHaveLength(4)
    expect(groupBySeverity(all).map((g) => g.severity)).toEqual(['critical', 'low', 'info'])
  })

  it('hides informational findings by default', () => {
    expect(visibleByDefault(all).map((f) => f.id)).toEqual(['a', 'b', 'd'])
  })
})

describe('history', () => {
  it('stores newest first and de-duplicates by file hash', () => {
    const store = memoryStore()
    addToHistory(report('aaa'), store, 1)
    addToHistory(report('bbb'), store, 2)
    const list = addToHistory(report('aaa'), store, 3)
    expect(list.map((e) => e.report.file.sha256)).toEqual(['aaa', 'bbb'])
    expect(loadHistory(store)).toHaveLength(2)
  })

  it('keeps at most MAX_ENTRIES', () => {
    const store = memoryStore()
    for (let i = 0; i < MAX_ENTRIES + 5; i++) addToHistory(report(`h${i}`), store, i)
    expect(loadHistory(store)).toHaveLength(MAX_ENTRIES)
  })

  it('survives corrupted data, missing storage and quota errors', () => {
    const store = memoryStore()
    store.setItem('apkguard.history', '{not json')
    expect(loadHistory(store)).toEqual([])
    expect(loadHistory(null)).toEqual([])
    const full: KeyValueStore = { ...store, setItem: () => { throw new Error('quota') } }
    expect(addToHistory(report('x'), full, 1)).toHaveLength(1)
  })

  it('clears', () => {
    const store = memoryStore()
    addToHistory(report('aaa'), store)
    clearHistory(store)
    expect(loadHistory(store)).toEqual([])
  })
})

describe('format helpers', () => {
  it('formats sizes', () => {
    expect(formatSize(512)).toBe('512 B')
    expect(formatSize(1536)).toBe('1.5 KB')
    expect(formatSize(5 * 1024 * 1024)).toBe('5.0 MB')
  })
  it('shortens hashes only when long', () => {
    expect(shortHash('abcd')).toBe('abcd')
    expect(shortHash('a'.repeat(64))).toBe(`${'a'.repeat(8)}…${'a'.repeat(8)}`)
  })
  it('formats relative time', () => {
    const now = 10_000_000
    expect(timeAgo(now - 5 * 60_000, 'en', now)).toBe('5 minutes ago')
    expect(timeAgo(now - 3 * 3600_000, 'en', now)).toBe('3 hours ago')
  })
  it('renders params for the technical view', () => {
    expect(formatParam(['a', 'b'])).toBe('a, b')
    expect(formatParam({ x: 1 })).toBe('{"x":1}')
    expect(formatParam(4)).toBe('4')
  })
})

describe('ui strings', () => {
  it('has every key in both languages', () => expect(missingTranslations()).toEqual([]))
  it('detects Italian only', () => {
    expect(detectLang('it-IT')).toBe('it')
    expect(detectLang('fr-FR')).toBe('en')
    expect(detectLang(undefined)).toBe('en')
  })
})
