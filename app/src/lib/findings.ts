import { SEVERITIES, type Finding, type Severity } from './types'

export type SeverityFilter = Severity | 'all'

export function countBySeverity(findings: Finding[]): Record<Severity, number> {
  const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 } as Record<Severity, number>
  for (const finding of findings) counts[finding.severity] += 1
  return counts
}

export function filterFindings(findings: Finding[], filter: SeverityFilter): Finding[] {
  return filter === 'all' ? findings : findings.filter((f) => f.severity === filter)
}

/** Groups findings by severity, most severe first, skipping empty groups. */
export function groupBySeverity(findings: Finding[]): { severity: Severity; items: Finding[] }[] {
  return SEVERITIES.map((severity) => ({
    severity,
    items: findings.filter((f) => f.severity === severity),
  })).filter((group) => group.items.length > 0)
}

/** Findings worth showing by default: informational ones are opt-in. */
export function visibleByDefault(findings: Finding[]): Finding[] {
  return findings.filter((f) => f.severity !== 'info')
}
