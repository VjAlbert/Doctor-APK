import { useCallback, useEffect, useRef, useState } from 'react'
import { analyzeFile, EngineError } from '../lib/client'
import { addToHistory, clearHistory, loadHistory, type HistoryEntry } from '../lib/history'
import { MODULES, type Lang, type Report } from '../lib/types'

/** The scan screen never flashes by: each stage stays visible a moment. */
const STEP_MS = 260
const MIN_SCAN_MS = 2600

export type Phase =
  | { kind: 'idle' }
  | { kind: 'scanning'; fileName: string; shown: number }
  | { kind: 'result'; report: Report; fromHistory: boolean; savedAt?: number }
  | { kind: 'error'; code: string; message: string }

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

export function useAnalysis(lang: Lang, vtKey?: string) {
  const [phase, setPhase] = useState<Phase>({ kind: 'idle' })
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory())
  const fileRef = useRef<File | null>(null)
  const runId = useRef(0)
  const renderedLang = useRef<Lang>(lang)

  const analyze = useCallback(
    async (file: File) => {
      const id = ++runId.current
      fileRef.current = file
      renderedLang.current = lang
      const started = performance.now()
      let engineDone = 0
      let shown = 0
      setPhase({ kind: 'scanning', fileName: file.name, shown: 0 })

      // Reveal stages at a human pace, never ahead of what the engine reported.
      const ticker = setInterval(() => {
        if (shown < engineDone && runId.current === id) {
          shown += 1
          setPhase({ kind: 'scanning', fileName: file.name, shown })
        }
      }, STEP_MS)

      try {
        const report = await analyzeFile(file, {
          lang,
          vtKey,
          onProgress: (e) => {
            if (e.state === 'done') engineDone = Math.max(engineDone, e.index)
          },
        })
        engineDone = MODULES.length
        while (runId.current === id && (shown < MODULES.length || performance.now() - started < MIN_SCAN_MS)) {
          await sleep(40)
        }
        if (runId.current !== id) return
        setHistory(addToHistory(report))
        setPhase({ kind: 'result', report, fromHistory: false })
      } catch (error) {
        if (runId.current !== id) return
        const known = error instanceof EngineError
        setPhase({
          kind: 'error',
          code: known ? error.code : 'unexpected',
          message: known ? error.message : String(error),
        })
      } finally {
        clearInterval(ticker)
      }
    },
    [lang, vtKey],
  )

  const openFromHistory = useCallback((entry: HistoryEntry) => {
    runId.current += 1
    fileRef.current = null
    setPhase({ kind: 'result', report: entry.report, fromHistory: true, savedAt: entry.savedAt })
  }, [])

  const reset = useCallback(() => {
    runId.current += 1
    fileRef.current = null
    setPhase({ kind: 'idle' })
  }, [])

  const retry = useCallback(() => {
    if (fileRef.current) void analyze(fileRef.current)
    else reset()
  }, [analyze, reset])

  const wipeHistory = useCallback(() => {
    clearHistory()
    setHistory([])
  }, [])

  // Switching language re-renders the report texts: re-run silently on the kept file.
  useEffect(() => {
    if (phase.kind !== 'result' || phase.fromHistory || !fileRef.current) return
    if (renderedLang.current === lang) return
    renderedLang.current = lang
    const id = ++runId.current
    analyzeFile(fileRef.current, { lang, vtKey })
      .then((report) => {
        if (runId.current === id) setPhase({ kind: 'result', report, fromHistory: false })
      })
      .catch(() => {
        /* keep showing the previous language rather than an error */
      })
  }, [lang, phase])

  return { phase, history, file: fileRef.current, analyze, openFromHistory, reset, retry, wipeHistory }
}
