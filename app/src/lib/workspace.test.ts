import { afterEach, describe, expect, it, vi } from 'vitest'
import { createProject, diffLineKind, draftIdea, getProposal, listProjects, STATUS_COLOR } from './workspace'
import type { Report } from './types'

const json = (status: number, body: unknown) =>
  Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))

afterEach(() => vi.unstubAllGlobals())

describe('diff line classification', () => {
  it.each([
    ['+++ b/SPEC.md', 'meta'], ['--- a/SPEC.md', 'meta'], ['@@ -1,3 +1,4 @@', 'hunk'],
    ['+added line', 'add'], ['-removed line', 'del'], [' unchanged', 'ctx'], ['', 'ctx'],
  ])('%s -> %s', (line, kind) => expect(diffLineKind(line)).toBe(kind))

  it('treats a removed line that starts with dashes as a removal', () => {
    expect(diffLineKind('-- comment')).toBe('del')
  })
})

describe('project client', () => {
  it('lists projects', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(200, { projects: [{ id: 'a-1234', name: 'A' }] })))
    expect(await listProjects()).toEqual([{ id: 'a-1234', name: 'A' }])
  })

  it('sends the ownership confirmation and the chosen options, never the file', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) => json(200, { id: 'x-1234', spec: 'template' }))
    vi.stubGlobal('fetch', fetchMock)
    const report = { verdict: { id: 'caution' }, app: { package: 'p' } } as unknown as Report
    await createProject({ report, codeId: 'c'.repeat(64), name: 'N', lang: 'it', ownerConfirmed: true, useAi: false })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/workspaces$/)
    expect(JSON.parse(String(init?.body))).toMatchObject({ owner_confirmed: true, use_ai: false, name: 'N', lang: 'it', code_id: 'c'.repeat(64) })
    expect(init?.headers).toEqual({ 'Content-Type': 'application/json' })
  })

  it('surfaces refusals with the engine message', async () => {
    vi.stubGlobal('fetch', vi.fn(() => json(403, { error: 'malicious', message: 'cannot recreate' })))
    await expect(createProject({ report: {} as Report, name: 'N', lang: 'en', ownerConfirmed: true, useAi: false }))
      .rejects.toMatchObject({ code: 'malicious', message: 'cannot recreate' })
  })

  it('encodes ids and language in the URLs', async () => {
    const fetchMock = vi.fn((_url: string, _init?: RequestInit) => json(200, {}))
    vi.stubGlobal('fetch', fetchMock)
    await getProposal('proj-1234', 'abcdef123456', 'it')
    await draftIdea('proj-1234', 'abcdef123456', 'en')
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/workspaces\/proj-1234\/proposals\/abcdef123456\?lang=it$/)
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/workspaces\/proj-1234\/ideas\/abcdef123456\/draft$/)
  })

  it('has a colour for every status', () => {
    for (const s of ['new', 'drafted', 'accepted', 'rejected', 'open', 'approved', 'stale', 'reverted']) expect(STATUS_COLOR[s]).toBeTruthy()
  })
})
