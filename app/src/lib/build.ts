import { engineRequest } from './http'

/** The commit this interface was built from (stamped by CI), or "dev". */
export const UI_BUILD: string = String(import.meta.env.VITE_BUILD ?? 'dev').slice(0, 7) || 'dev'

export interface EngineInfo {
  version: string
  build: string
}

/** The engine's identity. An engine from before builds were recorded answers without these fields. */
export async function getEngineInfo(): Promise<EngineInfo> {
  const body = await engineRequest<Partial<EngineInfo>>('/health')
  return { version: body.version ?? 'unknown', build: body.build ?? 'unknown' }
}

/** True when both parts are real builds and they differ: a sign of a mixed installation. */
export function buildsDiffer(ui: string, engine: string | undefined): boolean {
  return !!engine && ui !== 'dev' && engine !== 'dev' && ui !== engine   // 'unknown' (an old engine) differs too
}

/** True when a saved report was made by another engine build than the current one. */
export function isOlderReport(report: { engine?: { build: string } }, current: EngineInfo | null): boolean {
  if (!current) return false
  return !report.engine || report.engine.build !== current.build
}
