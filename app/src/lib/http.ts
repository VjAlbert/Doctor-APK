import { engineBase, EngineError } from './client'

/** One request to the local engine, turning failures into EngineError with the engine's own message. */
export async function engineRequest<T>(path: string, init?: RequestInit): Promise<T> {
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

export const jsonPost = (path: string, body: unknown) =>
  engineRequest<never>(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
