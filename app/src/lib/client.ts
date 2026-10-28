import { createNdjsonParser } from './ndjson'
import type { EngineEvent, Lang, ProgressEvent, Report } from './types'

const DEV_BASE: string = import.meta.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:8765'

export class EngineError extends Error {
  constructor(public code: string, message: string) {
    super(message)
  }
}

export interface BaseDeps {
  isTauri: boolean
  invoke: (command: string) => Promise<unknown>
  sleep: (ms: number) => Promise<void>
  devBase: string
  attempts?: number
}

/**
 * Where the engine listens. In the desktop app the sidecar picks a random port and
 * announces it to the shell, which the UI polls for; in the browser it is a fixed URL.
 */
export async function resolveEngineBase(deps: BaseDeps): Promise<string> {
  if (!deps.isTauri) return deps.devBase
  for (let attempt = 0; attempt < (deps.attempts ?? 100); attempt++) {
    const port = await deps.invoke('engine_port')
    if (typeof port === 'number') return `http://127.0.0.1:${port}`
    await deps.sleep(100)
  }
  throw new EngineError('engine_unreachable', 'The analysis engine did not start.')
}

let cachedBase: Promise<string> | null = null

export function engineBase(): Promise<string> {
  cachedBase ??= resolveEngineBase({
    isTauri: typeof window !== 'undefined' && '__TAURI_INTERNALS__' in window,
    invoke: async (command) => (await import('@tauri-apps/api/core')).invoke(command),
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    devBase: DEV_BASE,
  }).catch((error) => {
    cachedBase = null // let the next attempt retry
    throw error
  })
  return cachedBase
}

export interface AnalyzeOptions {
  lang: Lang
  category?: string
  /** VirusTotal API key; sent to the local engine only, and only when set. */
  vtKey?: string
  onProgress?: (event: ProgressEvent) => void
  signal?: AbortSignal
}

/** Sends the file to the local engine and resolves with the final report. */
export async function analyzeFile(file: File, options: AnalyzeOptions): Promise<Report> {
  const query = new URLSearchParams({ lang: options.lang, category: options.category ?? 'auto' })
  let response: Response
  try {
    response = await fetch(`${await engineBase()}/analyze?${query}`, {
      method: 'POST',
      body: file,
      headers: {
        'X-Filename': encodeURIComponent(file.name),
        ...(options.vtKey ? { 'X-VT-Key': options.vtKey } : {}),
      },
      signal: options.signal,
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
    if (error instanceof EngineError) throw error
    throw new EngineError('engine_unreachable', 'The analysis engine is not running.')
  }
  if (!response.ok || !response.body) {
    throw new EngineError('engine_unreachable', `Engine answered with status ${response.status}.`)
  }

  let report: Report | null = null
  let failure: EngineError | null = null
  const parser = createNdjsonParser((value) => {
    const event = value as EngineEvent
    if (event.event === 'progress') options.onProgress?.(event)
    else if (event.event === 'report') report = event.report
    else if (event.event === 'error') failure = new EngineError(event.code, event.message)
  })

  const reader = response.body.getReader()
  for (;;) {
    const { done, value } = await reader.read()
    if (done) break
    parser.push(value)
  }
  parser.end()

  if (failure) throw failure
  if (!report) throw new EngineError('no_report', 'The engine ended without a report.')
  return report
}
