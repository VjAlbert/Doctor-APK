import { engineBase, EngineError } from './client'
import type { Lang, Report } from './types'

export type AiState = 'not_installed' | 'not_logged_in' | 'connected'

export interface AiStatus {
  state: AiState
  version?: string | null
  auth?: 'subscription' | 'api_key' | 'other' | null
}

export interface AiExplanation {
  text: string
  cost_usd: number | null
  duration_ms: number | null
}

export interface AiPrompt {
  system: string
  prompt: string
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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

export const getAiStatus = () => request<AiStatus>('/ai/status')

function post<T>(report: Report, lang: Lang, dryRun: boolean): Promise<T> {
  return request<T>('/ai/explain', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ report, lang, dry_run: dryRun }),
  })
}

export const explainReport = (report: Report, lang: Lang) => post<AiExplanation>(report, lang, false)

/** What would be sent, without sending it: shown to the user before they trust the feature. */
export const previewExplanation = (report: Report, lang: Lang) => post<AiPrompt>(report, lang, true)
