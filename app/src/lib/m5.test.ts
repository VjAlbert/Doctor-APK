import { describe, expect, it } from 'vitest'
import { EngineError, resolveEngineBase } from './client'
import { closestExpected, diffFingerprint, groupHex } from './fingerprint'
import { buildPermissionRows, splitPermissions } from './permissions'
import { buildReportHtml, esc, reportFileName } from './reportHtml'
import { activeVtKey, DEFAULT_SETTINGS, loadSettings, saveSettings } from './settings'
import type { KeyValueStore } from './history'
import type { Finding, Report } from './types'

const permFinding = (permission: string, severity: Finding['severity']): Finding => ({
  id: 'manifest.permission', severity, module: 'manifest', params: { permission },
  text: { title: `title ${permission}`, description: `desc ${permission}`, advice: '' },
})

function report(overrides: Partial<Report> = {}): Report {
  return {
    file: { name: 'a.apk', size: 2048, kind: 'apk', md5: '', sha1: '', sha256: 'a'.repeat(64) },
    app: { package: 'com.acme.app', name: 'Acme', version_name: '1.0', version_code: '1', min_sdk: 21, target_sdk: 34 },
    certificates: [{ subject: 'CN=Acme', issuer: 'CN=Acme', sha256: 'b'.repeat(64), not_after: '2050-01-01T00:00:00' }],
    permissions: ['android.permission.INTERNET', 'android.permission.READ_SMS', 'android.permission.CAMERA'],
    iocs: {}, stats: {},
    authenticity: { status: 'unknown', label: 'Cannot be verified', sources: [], expected: [] },
    reputation: { status: 'disabled' },
    category: { id: 'unknown', source: 'auto', confidence: 'none' },
    verdict: {
      id: 'caution', level: 'medium', score: 33,
      counts: { critical: 0, high: 1, medium: 0, low: 0, info: 0 },
      reasons: [permFinding('READ_SMS', 'high')],
      text: { title: 'Proceed with caution', summary: 'Look closer.', limitations: 'Static analysis has limits.', category: 'unrecognized' },
    },
    findings: [permFinding('READ_SMS', 'high'), permFinding('CAMERA', 'low')],
    ...overrides,
  }
}

describe('permission rows', () => {
  it('joins permissions with findings and orders by severity', () => {
    const rows = buildPermissionRows(report())
    expect(rows.map((r) => r.name)).toEqual(['READ_SMS', 'CAMERA', 'INTERNET'])
    expect(rows[2].finding).toBeUndefined()
  })

  it('splits sensitive from other and filters by query', () => {
    const rows = buildPermissionRows(report())
    expect(splitPermissions(rows).sensitive).toHaveLength(2)
    expect(splitPermissions(rows).other.map((r) => r.name)).toEqual(['INTERNET'])
    expect(splitPermissions(rows, 'sms').sensitive.map((r) => r.name)).toEqual(['READ_SMS'])
    expect(splitPermissions(rows, 'title camera').sensitive.map((r) => r.name)).toEqual(['CAMERA'])
    expect(splitPermissions(rows, 'zzz')).toEqual({ sensitive: [], other: [] })
  })
})

describe('fingerprint comparison', () => {
  const a = '0123456789abcdef'.repeat(4)

  it('groups hex in blocks', () => {
    expect(groupHex('abcdefgh12345678', 8)).toEqual(['abcdefgh', '12345678'])
    expect(groupHex('abc', 8)).toEqual(['abc'])
  })

  it('marks matching and differing blocks, ignoring case', () => {
    const changed = a.slice(0, 8) + 'ffffffff' + a.slice(16)
    const diff = diffFingerprint(changed.toUpperCase(), a)
    expect(diff.map((g) => g.same)).toEqual([true, false, true, true, true, true, true, true])
  })

  it('picks the closest expected fingerprint', () => {
    const near = a.slice(0, 56) + '00000000'
    const far = 'f'.repeat(64)
    expect(closestExpected(a, [far, near])).toBe(1)
  })
})

describe('settings', () => {
  const store = (initial?: string): KeyValueStore & { value: string | null } => {
    const s = { value: initial ?? null, getItem: () => s.value, setItem: (_: string, v: string) => { s.value = v }, removeItem: () => { s.value = null } }
    return s
  }
  const key = 'a1'.repeat(32)

  it('round-trips and defaults safely', () => {
    const s = store()
    saveSettings({ vtEnabled: true, vtKey: key }, s)
    expect(loadSettings(s)).toEqual({ vtEnabled: true, vtKey: key })
    expect(loadSettings(store('{broken'))).toEqual(DEFAULT_SETTINGS)
    expect(loadSettings(null)).toEqual(DEFAULT_SETTINGS)
    expect(loadSettings(store('{"vtEnabled":"yes","vtKey":5}'))).toEqual(DEFAULT_SETTINGS)
  })

  it('only offers a key when the check is on and the key looks valid', () => {
    expect(activeVtKey({ vtEnabled: true, vtKey: ` ${key} ` })).toBe(key)
    expect(activeVtKey({ vtEnabled: false, vtKey: key })).toBeUndefined()
    expect(activeVtKey({ vtEnabled: true, vtKey: 'short' })).toBeUndefined()
    expect(activeVtKey({ vtEnabled: true, vtKey: 'bad key with spaces and symbols!!' })).toBeUndefined()
  })
})

describe('HTML report', () => {
  it('escapes everything that comes from the APK', () => {
    const evil = '<img src=x onerror=alert(1)>"\'&'
    const html = buildReportHtml(report({
      app: { package: evil, name: evil, version_name: evil, version_code: null, min_sdk: null, target_sdk: null },
      file: { name: evil, size: 1, kind: 'apk', md5: '', sha1: '', sha256: 'c'.repeat(64) },
      certificates: [{ subject: evil, issuer: evil, sha256: 'd'.repeat(64), not_after: '2050' }],
      permissions: [evil],
      findings: [{ ...permFinding('X', 'high'), text: { title: evil, description: evil, advice: evil, note: evil } }],
      verdict: { ...report().verdict, reasons: [], text: { title: evil, summary: evil, limitations: evil, category: evil } },
    }), 'en')
    expect(html).not.toContain('<img')
    expect(html).not.toMatch(/onerror=alert\(1\)>/)
    expect(html).toContain('&lt;img src=x onerror=alert(1)&gt;')
  })

  it('is self-contained: no scripts or external resources', () => {
    const html = buildReportHtml(report(), 'it', new Date('2026-01-02T03:04:05Z'))
    expect(html).not.toMatch(/<script|<link|<img|src=|https?:\/\//i)
    expect(html).toContain('lang="it"')
    expect(html).toContain('Look closer.')
  })

  it('lists permissions and hides informational findings by default', () => {
    const info: Finding = { ...permFinding('NOPE', 'info'), text: { title: 'secret info', description: '', advice: '' } }
    const html = buildReportHtml(report({ findings: [...report().findings, info] }), 'en')
    expect(html).toContain('android.permission.INTERNET')
    expect(html).not.toContain('secret info')
  })

  it('builds a safe file name', () => {
    expect(reportFileName(report())).toBe('apkguard-com.acme.app.html')
    expect(reportFileName(report({ app: { ...report().app, package: '../../etc/pass wd' } }))).toBe('apkguard-.._.._etc_pass_wd.html')
    expect(esc(5)).toBe('5')
  })
})


describe('engine base url', () => {
  const sleep = async () => {}

  it('uses the fixed dev url in a browser, without asking the shell', async () => {
    const invoke = async () => { throw new Error('must not be called') }
    expect(await resolveEngineBase({ isTauri: false, invoke, sleep, devBase: 'http://127.0.0.1:8765' })).toBe('http://127.0.0.1:8765')
  })

  it('polls the desktop shell until the engine announces its port', async () => {
    const answers: unknown[] = [null, null, 41234]
    const invoke = async () => answers.shift()
    expect(await resolveEngineBase({ isTauri: true, invoke, sleep, devBase: 'x' })).toBe('http://127.0.0.1:41234')
  })

  it('gives up with an engine error if the port never shows up', async () => {
    const invoke = async () => null
    await expect(resolveEngineBase({ isTauri: true, invoke, sleep, devBase: 'x', attempts: 3 }))
      .rejects.toMatchObject({ code: 'engine_unreachable' })
    expect(new EngineError('c', 'm').code).toBe('c')
  })
})
