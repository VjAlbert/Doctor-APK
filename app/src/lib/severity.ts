import type { RiskLevel, Severity } from './types'

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: '#ff3b6b',
  high: '#ff7a45',
  medium: '#fbbf24',
  low: '#38bdf8',
  info: '#8a9bb2',
}

export const LEVEL_COLOR: Record<RiskLevel, string> = {
  low: '#34d399',
  medium: '#fbbf24',
  high: '#ff7a45',
  critical: '#ff3b6b',
}
