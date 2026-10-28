import { LEVEL_COLOR } from '../lib/severity'
import { timeAgo } from '../lib/format'
import { useLang } from '../lib/lang'
import type { HistoryEntry } from '../lib/history'
import { TrashIcon } from './Icons'

interface Props {
  entries: HistoryEntry[]
  onOpen: (entry: HistoryEntry) => void
  onClear: () => void
}

export function HistoryList({ entries, onOpen, onClear }: Props) {
  const { t, lang } = useLang()
  return (
    <section aria-labelledby="recent" className="glass flex h-full min-h-0 flex-col rounded-2xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h2 id="recent" className="font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('home.recent')}</h2>
        {entries.length > 0 && (
          <button type="button" onClick={onClear} title={t('home.clear')} aria-label={t('home.clear')}
            className="rounded-md p-1 text-dim transition hover:text-ink"><TrashIcon size={16} /></button>
        )}
      </div>
      {entries.length === 0 ? (
        <p className="m-auto max-w-[16rem] text-center text-sm text-dim">{t('home.empty')}</p>
      ) : (
        <ul className="scroll -mr-2 flex min-h-0 flex-1 flex-col gap-1.5 overflow-y-auto pr-2">
          {entries.map((entry) => {
            const { report } = entry
            const color = LEVEL_COLOR[report.verdict.level]
            return (
              <li key={entry.id}>
                <button type="button" onClick={() => onOpen(entry)}
                  className="group flex w-full items-center gap-3 rounded-xl border border-transparent px-3 py-2.5 text-left transition hover:border-line-strong hover:bg-white/[.03]">
                  <span className="grid size-10 shrink-0 place-items-center rounded-lg font-mono text-sm font-semibold"
                    style={{ color, background: `${color}18`, border: `1px solid ${color}40` }}>
                    {report.verdict.score}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{report.app.name || report.file.name}</span>
                    <span className="block truncate font-mono text-[11px] text-dim">
                      {report.app.package} · {timeAgo(entry.savedAt, lang)}
                    </span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
