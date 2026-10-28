import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { EngineError } from '../lib/client'
import { explainCode, getSlice, indexCode, previewCodeExplanation, type Capability, type CodeMap, type CodeView as CodeSlice } from '../lib/code'
import { useLang } from '../lib/lang'
import { AiAnswerPanel } from './AiAnswerPanel'
import { InfoIcon, SparkIcon } from './Icons'

interface Props {
  file: File | null
  aiReady: boolean
}

const AMBER = '#fbbf24'

function Chip({ children, color = '#8a9bb2' }: { children: React.ReactNode; color?: string }) {
  return (
    <span className="rounded-full px-2.5 py-0.5 text-xs" style={{ color, background: `${color}18`, border: `1px solid ${color}40` }}>{children}</span>
  )
}

function CodeDrawer({ map, capability, aiReady, onClose }: { map: CodeMap; capability: Capability; aiReady: boolean; onClose: () => void }) {
  const { t, lang } = useLang()
  const [views, setViews] = useState<CodeSlice[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setViews(null)
    setError(null)
    getSlice(map.id, capability.id, lang)
      .then((r) => live && setViews(r.methods))
      .catch((e) => live && setError(e instanceof EngineError ? e.message : String(e)))
    return () => { live = false }
  }, [map.id, capability.id, lang])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <>
      <motion.div className="fixed inset-0 z-20 bg-black/55" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={onClose} aria-hidden="true" />
      <motion.aside role="dialog" aria-modal="true" aria-label={capability.title}
        className="glass fixed inset-y-0 right-0 z-30 flex w-full max-w-2xl flex-col gap-4 overflow-y-auto p-7"
        initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }}>
        <header className="flex items-start justify-between gap-4">
          <div>
            <h2 className="text-xl font-semibold">{capability.title}</h2>
            <p className="mt-1 text-sm text-muted">{capability.description}</p>
          </div>
          <button type="button" onClick={onClose} className="shrink-0 rounded-lg border border-line-strong px-3 py-1.5 text-sm text-muted hover:text-ink">{t('code.close')}</button>
        </header>
        {aiReady && (
          <AiAnswerPanel
            ask={() => explainCode(map.id, capability.id, lang)}
            preview={() => previewCodeExplanation(map.id, capability.id, lang)}
            resetKey={`${map.id}-${capability.id}-${lang}`}
            buttonLabel="code.explain" title="ai.result" />
        )}
        <p className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.16em] text-dim"><InfoIcon size={14} />{t('code.readOnly')}</p>
        {error && <p className="text-sm text-caution" role="alert">{error}</p>}
        {!views && !error && <p className="text-sm text-muted">{t('code.loading')}</p>}
        {views?.map((view) => (
          <article key={`${view.class}.${view.signature}`} className="overflow-hidden rounded-xl border border-line" data-testid="code-view">
            <header className="flex flex-wrap items-center gap-2 border-b border-line bg-black/30 px-3.5 py-2">
              <code className="min-w-0 flex-1 truncate font-mono text-xs text-ink" title={`${view.class}.${view.method}`}>{view.class}.{view.method}</code>
              <Chip>{view.kind === 'decompiled' ? t('code.kindDecompiled') : t('code.kindBytecode')}</Chip>
              {view.third_party && <Chip color={AMBER}>{t('code.library')}</Chip>}
            </header>
            <pre className="scroll max-h-80 overflow-auto bg-black/40 p-3.5 font-mono text-[12px] leading-relaxed text-[#c9d6e6]">{view.source}</pre>
          </article>
        ))}
      </motion.aside>
    </>
  )
}

export function CodeView({ file, aiReady }: Props) {
  const { t, lang } = useLang()
  const [map, setMap] = useState<CodeMap | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [open, setOpen] = useState<Capability | null>(null)

  useEffect(() => {
    if (!file) return
    let live = true
    setMap(null)
    setError(null)
    indexCode(file, lang)
      .then((m) => live && setMap(m))
      .catch((e) => live && setError(e instanceof EngineError ? e.message : String(e)))
    return () => { live = false }
  }, [file, lang])

  if (!file) return <p className="glass mx-auto mt-10 max-w-xl rounded-2xl p-6 text-center text-sm text-muted">{t('code.needFile')}</p>
  if (error) return <p className="glass mx-auto mt-10 max-w-xl rounded-2xl p-6 text-center text-sm text-caution" role="alert">{error}</p>
  if (!map) {
    return (
      <p className="mx-auto mt-16 flex items-center justify-center gap-3 text-sm text-muted">
        <motion.span className="size-2.5 rounded-full bg-cyan" animate={{ opacity: [1, 0.25, 1] }} transition={{ repeat: Infinity, duration: 1 }} />
        {t('code.loading')}
      </p>
    )
  }

  return (
    <div className="scroll mx-auto h-full w-full max-w-4xl overflow-y-auto pb-8 pr-2">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('code.title')}</h1>
          <p className="font-mono text-xs text-dim">{t('code.stats').replace('{c}', String(map.stats.classes)).replace('{m}', String(map.stats.methods))}</p>
        </div>
      </div>
      <p className="mt-3 flex items-start gap-2 text-sm leading-relaxed text-muted"><InfoIcon size={16} className="mt-0.5 shrink-0" />{t('code.intro')}</p>

      <div className="mt-5">
        {aiReady ? (
          <AiAnswerPanel
            ask={() => explainCode(map.id, null, lang)}
            preview={() => previewCodeExplanation(map.id, null, lang)}
            resetKey={`${map.id}-all-${lang}`}
            buttonLabel="code.explainAll" title="code.overview" />
        ) : (
          <p className="flex items-center gap-2 text-sm text-dim"><SparkIcon size={15} />{t('code.connectHint')}</p>
        )}
      </div>

      <section className="mt-7">
        <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('code.can')}</h2>
        {map.capabilities.length === 0 ? (
          <p className="glass rounded-2xl p-5 text-sm text-muted">{t('code.noCaps')}</p>
        ) : (
          <ul className="grid gap-2.5">
            {map.capabilities.map((cap) => (
              <li key={cap.id} className="glass rounded-2xl px-5 py-4" style={{ borderLeft: `3px solid ${cap.sensitive ? AMBER : 'rgb(148 197 255 / .25)'}` }} data-testid="capability">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2.5">
                      <h3 className="font-semibold leading-snug">{cap.title}</h3>
                      {cap.sensitive && <Chip color={AMBER}>{t('code.sensitive')}</Chip>}
                    </div>
                    <p className="mt-1 text-sm text-muted">{cap.description}</p>
                    <p className="mt-1.5 font-mono text-[11.5px] text-dim">
                      {t('code.places')}: {cap.count} · {t('code.own')}: {cap.own_count}
                    </p>
                    <p className="mt-0.5 truncate font-mono text-[11.5px] text-dim" title={cap.sample.join(', ')}>{cap.sample.join(', ')}</p>
                  </div>
                  <button type="button" onClick={() => setOpen(cap)}
                    className="shrink-0 rounded-xl border border-line-strong px-3.5 py-2 text-sm text-ink transition hover:bg-white/[.05]">{t('code.viewCode')}</button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="mt-7">
        <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('code.starts')}</h2>
        <ul className="grid gap-2.5">
          {map.entry_points.map((entry) => (
            <li key={`${entry.kind}-${entry.name}`} className="glass rounded-2xl px-5 py-3.5" data-testid="entry-point">
              <p className="text-sm font-medium">{entry.label}</p>
              <p className="mt-0.5 break-all font-mono text-[11.5px] text-dim">{entry.name}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {entry.triggers.map((tr) => <Chip key={tr.id} color="#22d3ee">{tr.text}</Chip>)}
                {entry.exported && <Chip color={AMBER}>{t('code.exported')}</Chip>}
                {entry.links.map((l) => <Chip key={l.id} color="#a78bfa">{t('code.uses')}: {l.title}</Chip>)}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <AnimatePresence>
        {open && <CodeDrawer map={map} capability={open} aiReady={aiReady} onClose={() => setOpen(null)} />}
      </AnimatePresence>
    </div>
  )
}
