import type { Finding, Report, Severity } from './types'

export interface PermissionRow {
  name: string // short name, e.g. READ_SMS
  full: string
  finding?: Finding
  severity?: Severity
}

const ORDER: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3, info: 4 }

/** Joins the manifest's permission list with the findings the engine raised for them. */
export function buildPermissionRows(report: Report): PermissionRow[] {
  const byName = new Map<string, Finding>()
  for (const f of report.findings) {
    if (f.id === 'manifest.permission' && typeof f.params.permission === 'string') {
      byName.set(f.params.permission, f)
    }
  }
  return report.permissions
    .map((full) => {
      const name = full.slice(full.lastIndexOf('.') + 1)
      const finding = byName.get(name)
      return { name, full, finding, severity: finding?.severity }
    })
    .sort((a, b) => {
      const sa = a.severity ? ORDER[a.severity] : 9
      const sb = b.severity ? ORDER[b.severity] : 9
      return sa - sb || a.name.localeCompare(b.name)
    })
}

export function splitPermissions(rows: PermissionRow[], query = '') {
  const q = query.trim().toLowerCase()
  const match = (r: PermissionRow) =>
    !q || r.full.toLowerCase().includes(q) || (r.finding?.text.title.toLowerCase().includes(q) ?? false)
  const visible = rows.filter(match)
  return {
    sensitive: visible.filter((r) => r.finding),
    other: visible.filter((r) => !r.finding),
  }
}
