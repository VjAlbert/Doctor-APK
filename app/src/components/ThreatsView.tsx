import { useMemo, useState } from 'react'
import { countBySeverity, filterFindings, groupBySeverity, visibleByDefault, type SeverityFilter } from '../lib/findings'
import { useLang } from '../lib/lang'
import { SEVERITY_COLOR } from '../lib/severity'
import { severityKey } from '../lib/ui'
import { SEVERITIES, type Report } from '../lib/types'
import { ArrowLeftIcon } from './Icons'
import { FindingCard } from './FindingCard'

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer select-none items-center gap-2.5 text-sm text-muted">
      <button type="button" role="switch" aria-checked={checked} onClick={() => onChange(!checked)}
        className="relative h-5 w-9 rounded-full transition" style={{ background: checked ? '#22d3ee' : 'rgb(148 197 255 / .2)' }}>
        <span className="absolute top-0.5 size-4 rounded-full bg-white shadow transition-all" style={{ left: checked ? '1.1rem' : '0.125rem' }} />
      </button>
      {label}
    </label>
  )
}

export function ThreatsView({ report, onBack }: { report: Report; onBack: () => void }) {
  const { t } = useLang()
  const [filter, setFilter] = useState<SeverityFilter>('all')
  const [technical, setTechnical] = useState(false)
  const [showInfo, setShowInfo] = useState(false)

  const base = showInfo ? report.findings : visibleByDefault(report.findings)
  const counts = useMemo(() => countBySeverity(base), [base])
  const groups = useMemo(() => groupBySeverity(filterFindings(base, filter)), [base, filter])

  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-4xl flex-col">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <button type="button" onClick={onBack} aria-label={t('threats.back')}
            className="grid size-9 place-items-center rounded-xl border border-line-strong text-muted transition hover:text-ink">
            <ArrowLeftIcon size={18} />
          </button>
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">{t('threats.title')}</h1>
            <p className="font-mono text-xs text-dim">{report.app.name || report.file.name}</p>
          </div>
        </div>
        <div className="flex items-center gap-5">
          <Toggle checked={showInfo} onChange={setShowInfo} label={t('threats.showInfo')} />
          <Toggle checked={technical} onChange={setTechnical} label={t('threats.technical')} />
        </div>
      </div>

      <div className="mt-5 flex flex-wrap gap-2" role="group">
        {(['all', ...SEVERITIES] as SeverityFilter[]).map((key) => {
          const n = key === 'all' ? base.length : counts[key]
          if (key !== 'all' && n === 0) return null
          const active = filter === key
          const color = key === 'all' ? '#22d3ee' : SEVERITY_COLOR[key]
          return (
            <button key={key} type="button" onClick={() => setFilter(key)} aria-pressed={active}
              className="flex items-center gap-2 rounded-full px-3.5 py-1.5 text-sm transition"
              style={{ color: active ? '#070b11' : color, background: active ? color : `${color}14`, border: `1px solid ${color}55` }}>
              {key === 'all' ? t('threats.all') : t(severityKey(key))}
              <span className="font-mono text-xs opacity-80">{n}</span>
            </button>
          )
        })}
      </div>

      <div className="scroll -mr-3 mt-5 min-h-0 flex-1 overflow-y-auto pr-3 pb-6">
        {groups.length === 0 ? (
          <p className="py-16 text-center text-muted">{t('threats.empty')}</p>
        ) : (
          groups.map((group) => (
            <section key={group.severity} className="mb-6">
              <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em]" style={{ color: SEVERITY_COLOR[group.severity] }}>
                {t(severityKey(group.severity))} · {group.items.length}
              </h2>
              <div className="grid gap-2.5">
                {group.items.map((finding, i) => (
                  <FindingCard key={`${finding.id}-${finding.params.permission ?? i}`} finding={finding} technical={technical}
                    defaultOpen={group.severity === 'critical' && i === 0} />
                ))}
              </div>
            </section>
          ))
        )}
      </div>
    </div>
  )
}
