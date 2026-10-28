import { useMemo, useState } from 'react'
import { useLang } from '../lib/lang'
import { buildPermissionRows, splitPermissions } from '../lib/permissions'
import { SEVERITY_COLOR } from '../lib/severity'
import type { Report } from '../lib/types'
import { SearchIcon } from './Icons'
import { SeverityBadge } from './SeverityBadge'

export function PermissionsView({ report }: { report: Report }) {
  const { t } = useLang()
  const [query, setQuery] = useState('')
  const rows = useMemo(() => buildPermissionRows(report), [report])
  const { sensitive, other } = useMemo(() => splitPermissions(rows, query), [rows, query])

  return (
    <div className="mx-auto flex h-full min-h-0 w-full max-w-4xl flex-col">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('perm.title')}</h1>
          <p className="font-mono text-xs text-dim">{rows.length} {t('perm.total')}</p>
        </div>
        <label className="glass flex items-center gap-2 rounded-xl px-3.5 py-2 text-sm">
          <SearchIcon size={16} className="text-dim" />
          <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('perm.search')}
            className="w-56 bg-transparent outline-none placeholder:text-dim" aria-label={t('perm.search')} />
        </label>
      </div>

      <div className="scroll -mr-3 mt-5 min-h-0 flex-1 overflow-y-auto pr-3 pb-6">
        {sensitive.length === 0 && other.length === 0 && <p className="py-16 text-center text-muted">{t('perm.none')}</p>}
        {sensitive.length > 0 && (
          <section className="mb-7">
            <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('perm.sensitive')} · {sensitive.length}</h2>
            <ul className="grid gap-2.5">
              {sensitive.map(({ name, finding }) => finding && (
                <li key={name} className="glass rounded-2xl px-5 py-3.5" style={{ borderLeft: `3px solid ${SEVERITY_COLOR[finding.severity]}` }}>
                  <div className="mb-1 flex flex-wrap items-center gap-2.5">
                    <SeverityBadge severity={finding.severity} />
                    <code className="font-mono text-xs text-dim">{name}</code>
                  </div>
                  <p className="font-semibold leading-snug">{finding.text.title}</p>
                  <p className="mt-0.5 text-sm text-muted">{finding.text.description}</p>
                  {finding.text.note && <p className="mt-1.5 text-xs text-dim">{finding.text.note}</p>}
                </li>
              ))}
            </ul>
          </section>
        )}
        {other.length > 0 && (
          <section>
            <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('perm.other')} · {other.length}</h2>
            <ul className="flex flex-wrap gap-2">
              {other.map(({ name, full }) => (
                <li key={full} title={full} className="rounded-lg border border-line px-2.5 py-1 font-mono text-xs text-muted">{name}</li>
              ))}
            </ul>
          </section>
        )}
      </div>
    </div>
  )
}
