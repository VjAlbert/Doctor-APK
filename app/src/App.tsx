import { AnimatePresence, MotionConfig, motion } from 'framer-motion'
import { useState } from 'react'
import { DropZone } from './components/DropZone'
import { ErrorView } from './components/ErrorView'
import { HistoryList } from './components/HistoryList'
import { LockIcon } from './components/Icons'
import { Logo } from './components/Logo'
import { ScanView } from './components/ScanView'
import { ThreatsView } from './components/ThreatsView'
import { VerdictView } from './components/VerdictView'
import { useAnalysis } from './hooks/useAnalysis'
import { LangProvider, useLang } from './lib/lang'
import type { Lang } from './lib/types'

function LangToggle() {
  const { lang, setLang } = useLang()
  return (
    <div className="flex rounded-lg border border-line p-0.5 font-mono text-xs" role="group" aria-label="language">
      {(['it', 'en'] as Lang[]).map((code) => (
        <button key={code} type="button" onClick={() => setLang(code)} aria-pressed={lang === code}
          className="rounded-md px-2.5 py-1 uppercase transition"
          style={{ background: lang === code ? 'rgb(34 211 238 / .16)' : 'transparent', color: lang === code ? '#67e8f9' : '#8a9bb2' }}>
          {code}
        </button>
      ))}
    </div>
  )
}

function Home({ analysis }: { analysis: ReturnType<typeof useAnalysis> }) {
  const { t } = useLang()
  return (
    <div className="mx-auto grid h-full w-full max-w-6xl items-center gap-8 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
      <div>
        <h1 className="max-w-xl text-4xl font-semibold leading-[1.1] tracking-tight md:text-5xl">{t('home.title')}</h1>
        <p className="mt-4 max-w-lg text-[15px] leading-relaxed text-muted">{t('home.subtitle')}</p>
        <div className="mt-8"><DropZone onFile={(file) => void analysis.analyze(file)} /></div>
        <ul className="mt-6 flex flex-wrap gap-2.5 font-mono text-[11px] uppercase tracking-wider text-muted">
          {(['home.local', 'home.noUpload', 'home.explained'] as const).map((key) => (
            <li key={key} className="flex items-center gap-1.5 rounded-full border border-line px-3 py-1"><LockIcon size={12} />{t(key)}</li>
          ))}
        </ul>
      </div>
      <div className="h-[420px] lg:h-[480px]">
        <HistoryList entries={analysis.history} onOpen={analysis.openFromHistory} onClear={analysis.wipeHistory} />
      </div>
    </div>
  )
}

function Screen() {
  const { lang, t } = useLang()
  const analysis = useAnalysis(lang)
  const [view, setView] = useState<'verdict' | 'threats'>('verdict')
  const { phase } = analysis

  const key = phase.kind === 'result' ? `result-${view}` : phase.kind
  const goHome = () => { setView('verdict'); analysis.reset() }

  return (
    <div className="relative z-10 flex h-full flex-col">
      <header className="flex items-center justify-between px-8 py-5">
        <button type="button" onClick={goHome} aria-label="APKGuard"><Logo /></button>
        <div className="flex items-center gap-4">
          <span className="hidden font-mono text-[11px] uppercase tracking-[0.18em] text-dim sm:block">{t('tagline')}</span>
          <LangToggle />
        </div>
      </header>
      <main className="min-h-0 flex-1 px-8 pb-4">
        <AnimatePresence mode="wait">
          <motion.div key={key} className="h-full" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.28 }}>
            {phase.kind === 'idle' && <Home analysis={analysis} />}
            {phase.kind === 'scanning' && <div className="flex h-full items-center"><ScanView fileName={phase.fileName} shown={phase.shown} /></div>}
            {phase.kind === 'error' && <div className="flex h-full items-center"><ErrorView code={phase.code} message={phase.message} onRetry={analysis.retry} onBack={goHome} /></div>}
            {phase.kind === 'result' && view === 'verdict' && (
              <div className="scroll h-full overflow-y-auto pb-8"><div className="flex min-h-full items-center">
                <VerdictView report={phase.report} onViewAll={() => setView('threats')} onAnother={goHome} />
              </div></div>
            )}
            {phase.kind === 'result' && view === 'threats' && <ThreatsView report={phase.report} onBack={() => setView('verdict')} />}
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="px-8 pb-4 text-center text-xs text-dim">{t('footer')}</footer>
    </div>
  )
}

export default function App() {
  return (
    <MotionConfig reducedMotion="user">
      <LangProvider>
        <div className="backdrop" aria-hidden="true" />
        <Screen />
      </LangProvider>
    </MotionConfig>
  )
}
