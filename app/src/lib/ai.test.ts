import { afterEach, describe, expect, it, vi } from 'vitest'
import { explainReport, getAiStatus, previewExplanation } from './ai'
import { parseBlocks, parseInline } from './miniMarkdown'
import type { Report } from './types'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))

afterEach(() => vi.unstubAllGlobals())

describe('ai client', () => {
  it('reads the connection status', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(200, { state: 'connected', version: '2.1', auth: 'subscription' })))
    expect(await getAiStatus()).toMatchObject({ state: 'connected', auth: 'subscription' })
  })

  it('sends the report with the language and the dry-run flag, as JSON to the local engine', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) => json(200, { text: 'ok', cost_usd: null, duration_ms: null }))
    vi.stubGlobal('fetch', fetchMock)
    const report = { verdict: { id: 'caution' } } as unknown as Report
    await explainReport(report, 'it')
    await previewExplanation(report, 'en')
    const [firstUrl, firstInit] = fetchMock.mock.calls[0]
    expect(firstUrl).toMatch(/^http:\/\/127\.0\.0\.1:\d+\/ai\/explain$/)
    expect(JSON.parse(String(firstInit?.body))).toMatchObject({ lang: 'it', dry_run: false })
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toMatchObject({ lang: 'en', dry_run: true })
    expect(firstInit?.headers).toEqual({ 'Content-Type': 'application/json' }) // no credentials of any kind
  })

  it('surfaces the engine error code and message', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(503, { error: 'not_logged_in', message: 'sign in first' })))
    await expect(getAiStatus()).rejects.toMatchObject({ code: 'not_logged_in', message: 'sign in first' })
  })

  it('reports an unreachable engine', async () => {
    vi.stubGlobal('fetch', vi.fn(() => Promise.reject(new TypeError('fetch failed'))))
    await expect(getAiStatus()).rejects.toMatchObject({ code: 'engine_unreachable' })
  })
})

describe('mini markdown', () => {
  it('splits bold text', () => {
    expect(parseInline('a **b** c')).toEqual([
      { text: 'a ', bold: false }, { text: 'b', bold: true }, { text: ' c', bold: false },
    ])
  })

  it('groups consecutive bullets and keeps paragraphs', () => {
    const blocks = parseBlocks('Intro line\n\n- **One:** first\n- Two\n\nClosing')
    expect(blocks.map((b) => b.type)).toEqual(['p', 'ul', 'p'])
    expect(blocks[1].type === 'ul' && blocks[1].items).toHaveLength(2)
  })

  it('treats HTML as plain text, never as markup', () => {
    const [block] = parseBlocks('<img src=x onerror=alert(1)>')
    expect(block).toEqual({ type: 'p', inline: [{ text: '<img src=x onerror=alert(1)>', bold: false }] })
  })

  it('drops heading markers', () => {
    expect(parseBlocks('## Title')[0]).toEqual({ type: 'p', inline: [{ text: 'Title', bold: false }] })
  })
})
