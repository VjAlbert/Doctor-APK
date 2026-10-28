import { SEVERITY_COLOR } from '../lib/severity'
import { severityKey } from '../lib/ui'
import { useLang } from '../lib/lang'
import type { Severity } from '../lib/types'

export function SeverityBadge({ severity }: { severity: Severity }) {
  const { t } = useLang()
  const color = SEVERITY_COLOR[severity]
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 font-mono text-[11px] font-medium uppercase tracking-wider"
      style={{ color, background: `${color}1f`, border: `1px solid ${color}44` }}>
      <span className="size-1.5 rounded-full" style={{ background: color, boxShadow: `0 0 8px ${color}` }} />
      {t(severityKey(severity))}
    </span>
  )
}
