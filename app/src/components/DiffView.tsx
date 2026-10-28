import { diffLineKind } from '../lib/workspace'
import type { FileChange } from '../lib/workspace'
import { useLang } from '../lib/lang'

const COLORS = {
  add: { color: '#7ee2b8', background: 'rgb(52 211 153 / .10)' },
  del: { color: '#ff9b9b', background: 'rgb(255 92 92 / .10)' },
  hunk: { color: '#67e8f9', background: 'rgb(34 211 238 / .07)' },
  meta: { color: '#8a9bb2', background: 'transparent' },
  ctx: { color: '#c9d6e6', background: 'transparent' },
} as const

/** One file's differences, coloured line by line. */
export function DiffView({ change }: { change: FileChange }) {
  const { t } = useLang()
  return (
    <article className="overflow-hidden rounded-xl border border-line" data-testid="diff">
      <header className="flex flex-wrap items-center gap-3 border-b border-line bg-black/30 px-3.5 py-2">
        <code className="min-w-0 flex-1 truncate font-mono text-xs">{change.path}</code>
        {change.is_new && <span className="rounded-full bg-cyan/10 px-2 py-0.5 text-[11px] text-cyan">{t('rev.new')}</span>}
        <span className="font-mono text-xs text-ok">+{change.added}</span>
        <span className="font-mono text-xs text-danger">-{change.removed}</span>
      </header>
      <pre className="scroll max-h-96 overflow-auto bg-black/40 py-2 font-mono text-[12px] leading-relaxed">
        {change.diff.map((line, i) => {
          const style = COLORS[diffLineKind(line)]
          return <div key={i} className="whitespace-pre px-3.5" style={style}>{line || ' '}</div>
        })}
        {change.truncated && <div className="px-3.5 text-dim">… {t('rev.truncated')}</div>}
      </pre>
    </article>
  )
}
