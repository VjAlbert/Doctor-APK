import { useLang } from '../lib/lang'
import { AlertIcon, TerminalIcon } from './Icons'

interface Props {
  code: string
  message: string
  onRetry: () => void
  onBack: () => void
}

export function ErrorView({ code, message, onRetry, onBack }: Props) {
  const { t } = useLang()
  const engineDown = code === 'engine_unreachable'
  return (
    <div className="glass mx-auto flex w-full max-w-lg flex-col items-center gap-4 rounded-3xl px-8 py-10 text-center" role="alert">
      <span className="grid size-14 place-items-center rounded-full text-danger" style={{ background: 'rgb(255 92 92 / .12)', border: '1px solid rgb(255 92 92 / .4)' }}>
        <AlertIcon size={28} />
      </span>
      <h1 className="text-xl font-semibold">{t('error.title')}</h1>
      <p className="text-sm leading-relaxed text-muted">{engineDown ? t('error.engine') : message}</p>
      {engineDown && (
        <code className="flex items-center gap-2 rounded-lg bg-black/40 px-3 py-2 font-mono text-xs text-cyan">
          <TerminalIcon size={14} />apkguard serve
        </code>
      )}
      <div className="mt-2 flex gap-3">
        <button type="button" onClick={onRetry} className="rounded-xl px-5 py-2 text-sm font-semibold text-bg" style={{ background: '#22d3ee' }}>{t('error.retry')}</button>
        <button type="button" onClick={onBack} className="rounded-xl border border-line-strong px-5 py-2 text-sm">{t('error.back')}</button>
      </div>
    </div>
  )
}
