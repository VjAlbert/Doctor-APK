import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useLang } from '../lib/lang'
import { VT_KEY_PATTERN, type Settings } from '../lib/settings'

interface Props {
  open: boolean
  settings: Settings
  onChange: (settings: Settings) => void
  onClose: () => void
  onClearHistory: () => void
}

export function SettingsDrawer({ open, settings, onChange, onClose, onClearHistory }: Props) {
  const { t } = useLang()
  const [reveal, setReveal] = useState(false)

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  const keyInvalid = settings.vtEnabled && settings.vtKey.trim() !== '' && !VT_KEY_PATTERN.test(settings.vtKey.trim())

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="fixed inset-0 z-20 bg-black/55" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            onClick={onClose} aria-hidden="true" />
          <motion.aside role="dialog" aria-modal="true" aria-label={t('settings.title')}
            className="glass fixed inset-y-0 right-0 z-30 flex w-full max-w-md flex-col gap-6 overflow-y-auto p-7"
            initial={{ x: '100%' }} animate={{ x: 0 }} exit={{ x: '100%' }} transition={{ type: 'spring', stiffness: 320, damping: 34 }}>
            <header className="flex items-center justify-between">
              <h2 className="text-xl font-semibold">{t('settings.title')}</h2>
              <button type="button" onClick={onClose} className="rounded-lg border border-line-strong px-3 py-1.5 text-sm text-muted hover:text-ink">{t('settings.close')}</button>
            </header>

            <section className="grid gap-3">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="font-medium">{t('settings.vt')}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted">{t('settings.vtHelp')}</p>
                </div>
                <button type="button" role="switch" aria-checked={settings.vtEnabled} aria-label={t('settings.vt')}
                  onClick={() => onChange({ ...settings, vtEnabled: !settings.vtEnabled })}
                  className="relative mt-1 h-6 w-11 shrink-0 rounded-full transition" style={{ background: settings.vtEnabled ? '#22d3ee' : 'rgb(148 197 255 / .2)' }}>
                  <span className="absolute top-0.5 size-5 rounded-full bg-white shadow transition-all" style={{ left: settings.vtEnabled ? '1.3rem' : '0.125rem' }} />
                </button>
              </div>
              {settings.vtEnabled && (
                <div className="grid gap-2">
                  <label className="text-sm text-muted" htmlFor="vt-key">{t('settings.vtKey')}</label>
                  <div className="flex gap-2">
                    <input id="vt-key" type={reveal ? 'text' : 'password'} value={settings.vtKey} autoComplete="off" spellCheck={false}
                      onChange={(e) => onChange({ ...settings, vtKey: e.target.value })}
                      className="min-w-0 flex-1 rounded-xl border border-line-strong bg-black/30 px-3.5 py-2 font-mono text-sm outline-none focus:border-cyan" />
                    <button type="button" onClick={() => setReveal((v) => !v)} className="rounded-xl border border-line-strong px-3 text-sm text-muted">
                      {reveal ? t('settings.hide') : t('settings.show')}
                    </button>
                  </div>
                  {keyInvalid && <p className="text-xs text-caution" role="alert">{t('settings.vtInvalid')}</p>}
                  <p className="text-xs text-dim">{t('settings.vtStorage')}</p>
                </div>
              )}
            </section>

            <section className="grid gap-2 border-t border-line pt-5">
              <h3 className="font-medium">{t('settings.history')}</h3>
              <button type="button" onClick={onClearHistory} className="w-fit rounded-xl border border-line-strong px-4 py-2 text-sm text-muted hover:text-ink">{t('home.clear')}</button>
            </section>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
