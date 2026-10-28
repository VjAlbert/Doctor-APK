import { AnimatePresence, MotionConfig, motion } from 'framer-motion'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { DropZone } from './components/DropZone'
import { CodeView } from './components/CodeView'
import { ErrorView } from './components/ErrorView'
import { ExplainPanel } from './components/ExplainPanel'
import { HistoryList } from './components/HistoryList'
import { ExportMenu } from './components/ExportMenu'
import { FolderIcon, GearIcon, LockIcon } from './components/Icons'
import { PermissionsView } from './components/PermissionsView'
import { ProjectsView } from './components/ProjectsView'
import { SettingsDrawer } from './components/SettingsDrawer'
import { SignatureView } from './components/SignatureView'
import { Tabs, type ResultView } from './components/Tabs'
import { Logo } from './components/Logo'
import { ScanView } from './components/ScanView'
import { ThreatsView } from './components/ThreatsView'
import { VerdictView } from './components/VerdictView'
import { useAnalysis } from './hooks/useAnalysis'
import { getAiStatus, type AiStatus } from './lib/ai'
import { getEngineInfo, isOlderReport, type EngineInfo } from './lib/build'
import { EngineError } from './lib/client'
import { LangProvider, useLang } from './lib/lang'
import { activeVtKey, loadSettings, saveSettings, type Settings } from './lib/settings'
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
  const [settings, setSettings] = useState<Settings>(() => loadSettings())
  const [settingsOpen, setSettingsOpen] = useState(false)
  useEffect(() => saveSettings(settings), [settings])
  const vtKey = useMemo(() => activeVtKey(settings), [settings])
  const [aiStatus, setAiStatus] = useState<AiStatus | null>(null)
  const [aiChecking, setAiChecking] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [engineInfo, setEngineInfo] = useState<EngineInfo | null>(null)
  useEffect(() => { void getEngineInfo().then(setEngineInfo).catch(() => setEngineInfo(null)) }, [])

  const checkAi = useCallback(async (connect: boolean) => {
    setAiChecking(true)
    setAiError(null)
    try {
      const status = await getAiStatus()
      setAiStatus(status)
      // Consent is recorded only when the user pressed Connect and a signed-in Claude Code was found.
      if (connect) setSettings((s) => ({ ...s, aiEnabled: status.state === 'connected' }))
    } catch (error) {
      setAiStatus(null)
      setAiError(error instanceof EngineError ? error.message : String(error))
    } finally {
      setAiChecking(false)
    }
  }, [])

  // Re-check quietly when the app starts with the feature already enabled.
  useEffect(() => {
    if (settings.aiEnabled) void checkAi(false)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  const analysis = useAnalysis(lang, vtKey)
  const [view, setView] = useState<ResultView>('verdict')
  const [section, setSection] = useState<'analyze' | 'projects'>('analyze')
  const [openProject, setOpenProject] = useState<string | null>(null)
  const { phase } = analysis
  const aiReady = settings.aiEnabled && aiStatus?.state === 'connected'

  const key = section === 'projects' ? `projects-${openProject ?? 'list'}` : phase.kind === 'result' ? `result-${view}` : phase.kind
  const goHome = () => { setView('verdict'); setSection('analyze'); analysis.reset() }
  const showProjects = (id: string | null = null) => { setOpenProject(id); setSection('projects') }

  return (
    <div className="relative z-10 flex h-full flex-col">
      <header className="flex items-center justify-between px-8 py-5">
        <button type="button" onClick={goHome} aria-label="APKGuard"><Logo /></button>
        <div className="flex items-center gap-4">
          <span className="hidden font-mono text-[11px] uppercase tracking-[0.18em] text-dim sm:block">{t('tagline')}</span>
          <LangToggle />
          <button type="button" onClick={() => showProjects()} aria-label={t('nav.projects')} title={t('nav.projects')}
            className="flex h-8 items-center gap-2 rounded-lg border border-line px-3 text-sm text-muted transition hover:text-ink"
            style={section === 'projects' ? { color: '#e6edf6', borderColor: 'rgb(34 211 238 / .5)' } : undefined}>
            <FolderIcon size={16} /><span className="hidden sm:inline">{t('nav.projects')}</span></button>
          <button type="button" onClick={() => setSettingsOpen(true)} aria-label={t('settings.open')} title={t('settings.open')}
            className="grid size-8 place-items-center rounded-lg border border-line text-muted transition hover:text-ink"><GearIcon size={17} /></button>
        </div>
      </header>
      {section === 'analyze' && phase.kind === 'result' && phase.fromHistory && (
        <div className="mx-8 mb-3 rounded-xl border px-4 py-2.5 text-sm" role="status" data-testid="history-banner"
          style={isOlderReport(phase.report, engineInfo) ? { borderColor: 'rgb(251 191 36 / .5)', background: 'rgb(251 191 36 / .08)', color: '#fcd34d' } : { borderColor: 'rgb(148 197 255 / .2)', color: '#8a9bb2' }}>
          {t('hist.banner')} {phase.savedAt ? new Date(phase.savedAt).toLocaleString(lang) : ''},{' '}
          {phase.report.engine ? t('hist.withEngine').replace('{v}', `${phase.report.engine.version} (${phase.report.engine.build})`) : t('hist.withUnknown')}.
          {isOlderReport(phase.report, engineInfo) && <> {t('hist.older')}</>}
        </div>
      )}
      {section === 'analyze' && phase.kind === 'result' && (
        <div className="flex flex-wrap items-center justify-between gap-3 px-8 pb-3">
          <Tabs view={view} onChange={setView} />
          <ExportMenu report={phase.report} />
        </div>
      )}
      <main className="min-h-0 flex-1 px-8 pb-4">
        <AnimatePresence mode="wait">
          <motion.div key={key} className="h-full" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }} transition={{ duration: 0.28 }}>
            {section === 'projects' && <ProjectsView key={openProject ?? 'list'} aiReady={aiReady} initialId={openProject} />}
            {section === 'analyze' && phase.kind === 'idle' && <Home analysis={analysis} />}
            {section === 'analyze' && phase.kind === 'scanning' && <div className="flex h-full items-center"><ScanView fileName={phase.fileName} shown={phase.shown} /></div>}
            {section === 'analyze' && phase.kind === 'error' && <div className="flex h-full items-center"><ErrorView code={phase.code} message={phase.message} onRetry={analysis.retry} onBack={goHome} /></div>}
            {section === 'analyze' && phase.kind === 'result' && view === 'verdict' && (
              <div className="scroll h-full overflow-y-auto pb-8"><div className="flex min-h-full items-center">
                <VerdictView report={phase.report} onViewAll={() => setView('threats')} onAnother={goHome}
                  extra={aiReady ? <ExplainPanel report={phase.report} /> : undefined} />
              </div></div>
            )}
            {section === 'analyze' && phase.kind === 'result' && view === 'threats' && <ThreatsView report={phase.report} onBack={() => setView('verdict')} />}
            {section === 'analyze' && phase.kind === 'result' && view === 'permissions' && <PermissionsView report={phase.report} />}
            {section === 'analyze' && phase.kind === 'result' && view === 'signature' && <SignatureView report={phase.report} />}
            {section === 'analyze' && phase.kind === 'result' && view === 'code' && (
              <CodeView report={phase.report} file={analysis.file} aiReady={aiReady} onCreated={(p) => showProjects(p.id)} />
            )}
          </motion.div>
        </AnimatePresence>
      </main>
      <footer className="px-8 pb-4 text-center text-xs text-dim">{t('footer')}</footer>
      <SettingsDrawer open={settingsOpen} settings={settings} onChange={setSettings} onClose={() => setSettingsOpen(false)}
        onClearHistory={analysis.wipeHistory}
        ai={{ status: aiStatus, checking: aiChecking, error: aiError }}
        engine={engineInfo}
        onConnectAi={() => void checkAi(true)}
        onDisconnectAi={() => setSettings((s) => ({ ...s, aiEnabled: false }))} />
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
