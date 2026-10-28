import { createNdjsonParser } from './ndjson'
import type { EngineEvent, Lang, ProgressEvent, Report } from './types'

const BASE: string = import.meta.env.VITE_ENGINE_URL ?? 'http://127.0.0.1:8765'

export class EngineError extends Error {
  constructor(public code: string, message: string) {
    super(message)
  }
}

export interface AnalyzeOptions {
  lang: Lang
  category?: string
  onProgress?: (event: ProgressEvent) => void
  signal?: AbortSignal
}

/** Sends the file to the local engine and resolves with the final report. */
export async function analyzeFile(file: File, options: AnalyzeOptions): Promise<Report> {
  const query = new URLSearchParams({ lang: options.lang, category: options.category ?? 'auto' })
  let response: Response
  try {
    response = await fetch(`${BASE}/analyze?${query}`, {
      method: 'POST',
      body: file,
      headers: { 'X-Filename': encodeURIComponent(file.name) },
      signal: options.signal,
    })
  } catch (error) {
    if (options.signal?.aborted) throw error
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
