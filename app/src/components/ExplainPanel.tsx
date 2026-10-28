import { motion } from 'framer-motion'
import { Fragment, useEffect, useRef, useState } from 'react'
import { explainReport, previewExplanation, type AiExplanation, type AiPrompt } from '../lib/ai'
import { EngineError } from '../lib/client'
import { useLang } from '../lib/lang'
import { parseBlocks, type Inline } from '../lib/miniMarkdown'
import type { Report } from '../lib/types'
import { InfoIcon, SparkIcon } from './Icons'

function Inlines({ parts }: { parts: Inline[] }) {
  return <>{parts.map((p, i) => (p.bold ? <strong key={i} className="font-semibold text-ink">{p.text}</strong> : <Fragment key={i}>{p.text}</Fragment>))}</>
}

type State =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'done'; answer: AiExplanation }
  | { kind: 'error'; message: string }

export function ExplainPanel({ report }: { report: Report }) {
  const { t, lang } = useLang()
  const [state, setState] = useState<State>({ kind: 'idle' })
  const [sent, setSent] = useState<AiPrompt | null>(null)
  const [showSent, setShowSent] = useState(false)
  const run = useRef(0)

  // A different report or language invalidates the previous answer.
  useEffect(() => {
    run.current += 1
    setState({ kind: 'idle' })
    setSent(null)
    setShowSent(false)
  }, [report, lang])

  const explain = async () => {
    const id = ++run.current
    setState({ kind: 'loading' })
    try {
      const answer = await explainReport(report, lang)
      if (run.current === id) setState({ kind: 'done', answer })
    } catch (error) {
      if (run.current === id) setState({ kind: 'error', message: error instanceof EngineError ? error.message : String(error) })
    }
  }

  const toggleSent = async () => {
    if (!showSent && !sent) {
      try {
        setSent(await previewExplanation(report, lang))
      } catch {
        return
      }
    }
    setShowSent((v) => !v)
  }

  return (
    <section className="glass rounded-2xl p-5" aria-live="polite" data-testid="explain-panel">
      {state.kind === 'idle' && (
        <button type="button" onClick={() => void explain()}
          className="flex items-center gap-2 rounded-xl px-4 py-2.5 text-sm font-semibold transition hover:brightness-110"
          style={{ color: '#d8b4fe', background: 'rgb(139 92 246 / .14)', border: '1px solid rgb(139 92 246 / .45)' }}>
          <SparkIcon size={17} />{t('ai.explain')}
        </button>
      )}
      {state.kind === 'loading' && (
        <p className="flex items-center gap-3 text-sm text-muted">
          <motion.span className="size-2.5 rounded-full bg-[#a78bfa]" animate={{ opacity: [1, 0.25, 1] }} transition={{ repeat: Infinity, duration: 1 }} />
          {t('ai.explaining')}
        </p>
      )}
      {state.kind === 'error' && (
        <div role="alert">
          <p className="text-sm font-semibold text-caution">{t('ai.error')}</p>
          <p className="mt-1 text-sm text-muted">{state.message}</p>
          <button type="button" onClick={() => void explain()} className="mt-3 rounded-lg border border-line-strong px-3 py-1.5 text-sm text-muted hover:text-ink">{t('ai.retry')}</button>
        </div>
      )}
      {state.kind === 'done' && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-[#c4b5fd]"><SparkIcon size={14} />{t('ai.result')}</h3>
          <div className="grid gap-2 text-[14.5px] leading-relaxed text-ink/90" data-testid="explain-text">
            {parseBlocks(state.answer.text).map((block, i) =>
              block.type === 'p' ? (
                <p key={i}><Inlines parts={block.inline} /></p>
              ) : (
                <ul key={i} className="grid list-disc gap-1.5 pl-5 marker:text-[#a78bfa]">
                  {block.items.map((item, j) => <li key={j}><Inlines parts={item} /></li>)}
                </ul>
              ),
            )}
          </div>
          <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-dim"><InfoIcon size={14} className="mt-0.5 shrink-0" />{t('ai.caveat')}</p>
        </div>
      )}
      {state.kind !== 'loading' && (
        <div className="mt-3">
          <button type="button" onClick={() => void toggleSent()} className="text-xs text-dim underline-offset-2 transition hover:text-ink hover:underline">
            {showSent ? t('ai.hideSent') : t('ai.showSent')}
          </button>
          {showSent && sent && (
            <pre className="scroll mt-2 max-h-56 overflow-auto rounded-xl bg-black/40 p-3 font-mono text-[11.5px] leading-relaxed text-muted" data-testid="sent-preview">{sent.prompt}</pre>
          )}
        </div>
      )}
    </section>
  )
}
