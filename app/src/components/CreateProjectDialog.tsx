import { motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { EngineError } from '../lib/client'
import { useLang } from '../lib/lang'
import type { Report } from '../lib/types'
import { createProject, type ProjectSummary } from '../lib/workspace'

interface Props {
  report: Report
  codeId?: string
  aiReady: boolean
  onClose: () => void
  onCreated: (project: ProjectSummary) => void
}

export function CreateProjectDialog({ report, codeId, aiReady, onClose, onCreated }: Props) {
  const { t, lang } = useLang()
  const [name, setName] = useState(report.app.name || report.app.package)
  const [owner, setOwner] = useState(false)
  const [useAi, setUseAi] = useState(aiReady)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && !busy && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [busy, onClose])

  const submit = async () => {
    setBusy(true)
    setError(null)
    try {
      onCreated(await createProject({ report, codeId, name, lang, ownerConfirmed: owner, useAi: useAi && aiReady }))
    } catch (e) {
      setError(e instanceof EngineError ? e.message : String(e))
      setBusy(false)
    }
  }

  return (
    <>
      <div className="fixed inset-0 z-20 bg-black/60" onClick={() => !busy && onClose()} aria-hidden="true" />
      <motion.div role="dialog" aria-modal="true" aria-label={t('proj.createTitle')}
        className="glass fixed left-1/2 top-1/2 z-30 w-full max-w-lg -translate-x-1/2 -translate-y-1/2 rounded-3xl p-7"
        initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }}>
        <h2 className="text-xl font-semibold">{t('proj.createTitle')}</h2>
        <label className="mt-5 block text-sm text-muted" htmlFor="proj-name">{t('proj.name')}</label>
        <input id="proj-name" value={name} onChange={(e) => setName(e.target.value)} maxLength={80}
          className="mt-1.5 w-full rounded-xl border border-line-strong bg-black/30 px-3.5 py-2 outline-none focus:border-cyan" />
        <label className="mt-5 flex cursor-pointer items-start gap-3 text-sm leading-relaxed">
          <input type="checkbox" checked={owner} onChange={(e) => setOwner(e.target.checked)} className="mt-1 size-4 accent-[#22d3ee]" data-testid="owner-check" />
          <span>{t('proj.owner')}</span>
        </label>
        {aiReady && (
          <label className="mt-3 flex cursor-pointer items-center gap-3 text-sm">
            <input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} className="size-4 accent-[#a78bfa]" />
            <span>{t('proj.useAi')}</span>
          </label>
        )}
        {!owner && <p className="mt-3 text-xs text-dim">{t('proj.ownerNeeded')}</p>}
        {error && <p className="mt-3 text-sm text-caution" role="alert">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button type="button" disabled={busy} onClick={onClose} className="rounded-xl border border-line-strong px-4 py-2 text-sm text-muted hover:text-ink disabled:opacity-50">{t('proj.cancel')}</button>
          <button type="button" disabled={!owner || busy || !name.trim()} onClick={() => void submit()}
            className="rounded-xl px-5 py-2 text-sm font-semibold text-bg disabled:opacity-40" style={{ background: '#22d3ee' }}>
            {busy ? t('proj.creating') : t('proj.confirm')}
          </button>
        </div>
      </motion.div>
    </>
  )
}
