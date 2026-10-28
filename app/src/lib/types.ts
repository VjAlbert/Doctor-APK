export type Lang = 'it' | 'en'
export type Severity = 'critical' | 'high' | 'medium' | 'low' | 'info'
export const SEVERITIES: Severity[] = ['critical', 'high', 'medium', 'low', 'info']

export interface FindingText {
  title: string
  description: string
  advice: string
  note?: string
}

export interface Finding {
  id: string
  severity: Severity
  module: string
  params: Record<string, unknown>
  text: FindingText
}

export type VerdictId = 'no_known_threats' | 'caution' | 'do_not_install'
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical'

export interface Verdict {
  id: VerdictId
  level: RiskLevel
  score: number
  counts: Record<Severity, number>
  reasons: Finding[]
  text: { title: string; summary: string; limitations: string; category: string }
}

export interface Report {
  file: { name: string; size: number; kind: string; md5: string; sha1: string; sha256: string }
  app: {
    package: string
    name: string | null
    version_name: string | null
    version_code: string | null
    min_sdk: number | null
    target_sdk: number | null
  }
  certificates: { subject: string; issuer: string; sha256: string; not_after: string }[]
  permissions: string[]
  iocs: { urls?: string[]; domains?: string[]; ips?: string[] }
  stats: Record<string, unknown>
  authenticity: { status: string; label: string; sources: string[] }
  category: { id: string; source: string; confidence: string }
  verdict: Verdict
  findings: Finding[]
}

export interface ProgressEvent {
  event: 'progress'
  module: string
  state: 'start' | 'done'
  index: number
  total: number
}

export type EngineEvent =
  | ProgressEvent
  | { event: 'report'; lang: Lang; report: Report }
  | { event: 'error'; code: string; message: string }

/** Engine pipeline stages, in execution order. */
export const MODULES = [
  'ingest', 'manifest', 'certificate', 'authenticity', 'dex', 'strings', 'payloads', 'yara', 'scoring',
] as const
