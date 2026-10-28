import { engineBase, EngineError } from './client'
import type { AiExplanation, AiPrompt } from './ai'
import type { Lang } from './types'

export interface Capability {
  id: string
  title: string
  description: string
  sensitive: boolean
  count: number
  own_count: number
  third_party_count: number
  sample: string[]
}

export interface EntryPoint {
  kind: string
  label: string
  name: string
  exported: boolean
  triggers: { id: string; text: string }[]
  links: { id: string; title: string }[]
}

export interface CodeMap {
  id: string
  package: string
  stats: { classes: number; methods: number; dex_files: number }
  timings?: { decode_ms: number; xref_ms: number; rules_ms: number }
  capabilities: Capability[]
  entry_points: EntryPoint[]
}

export interface CodeView {
  class: string
  method: string
  signature: string
  kind: 'decompiled' | 'bytecode'
  own: boolean
  third_party: boolean
  source: string
}

async function send<T>(path: string, init: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${await engineBase()}${path}`, init)
  } catch (error) {
    if (error instanceof EngineError) throw error
    throw new EngineError('engine_unreachable', 'The analysis engine is not running.')
  }
  let body: unknown = null
  try {
    body = await response.json()
  } catch {
    /* handled below */
  }
  if (!response.ok) {
    const failure = (body ?? {}) as { error?: string; message?: string }
    throw new EngineError(failure.error ?? 'failed', failure.message ?? `Engine answered with status ${response.status}.`)
  }
  return body as T
}

/** Uploads the APK to the local engine to read its code. The file never leaves the computer. */
export const indexCode = (file: File, lang: Lang) =>
  send<CodeMap>(`/code/index?lang=${lang}`, {
    method: 'POST',
    body: file,
    headers: { 'X-Filename': encodeURIComponent(file.name) },
  })

export const getSlice = (id: string, capability: string, lang: Lang) =>
  send<{ capability: string; methods: CodeView[] }>(`/code/${id}/slice?cap=${encodeURIComponent(capability)}&lang=${lang}`, { method: 'GET' })

function explain<T>(id: string, capability: string | null, lang: Lang, dryRun: boolean) {
  return send<T>(`/code/${id}/explain`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cap: capability, lang, dry_run: dryRun }),
  })
}

export const explainCode = (id: string, capability: string | null, lang: Lang) =>
  explain<AiExplanation>(id, capability, lang, false)
export const previewCodeExplanation = (id: string, capability: string | null, lang: Lang) =>
  explain<AiPrompt>(id, capability, lang, true)
