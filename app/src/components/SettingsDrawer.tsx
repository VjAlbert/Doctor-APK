import { AnimatePresence, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { useLang } from '../lib/lang'
import type { AiStatus } from '../lib/ai'
import { buildsDiffer, UI_BUILD, type EngineInfo } from '../lib/build'
import { VT_KEY_PATTERN, type Settings } from '../lib/settings'

interface Props {
  open: boolean
  settings: Settings
  onChange: (settings: Settings) => void
  onClose: () => void
  onClearHistory: () => void
  ai: { status: AiStatus | null; checking: boolean; error: string | null }
  onConnectAi: () => void
  onDisconnectAi: () => void
  engine: EngineInfo | null
}

export function SettingsDrawer({ open, settings, onChange, onClose, onClearHistory, ai, onConnectAi, onDisconnectAi, engine }: Props) {
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

            <section className="grid gap-3 border-t border-line pt-5" data-testid="ai-section">
              <h3 className="font-medium">{t('ai.title')}</h3>
              <p className="text-sm leading-relaxed text-muted">{t('ai.help')}</p>
              {settings.aiEnabled && ai.status?.state === 'connected' ? (
                <div className="grid gap-3">
                  <p className="flex flex-wrap items-center gap-2 text-sm">
                    <span className="size-2 rounded-full bg-ok" style={{ boxShadow: '0 0 8px #34d399' }} />
                    <span className="font-medium text-ok">{t('ai.connected')}</span>
                    <span className="text-muted">
                      {ai.status.auth === 'subscription' ? t('ai.viaSubscription') : ai.status.auth === 'api_key' ? t('ai.viaApiKey') : t('ai.viaOther')}
                    </span>
                    {ai.status.version && <span className="font-mono text-xs text-dim">{ai.status.version}</span>}
                  </p>
                  <button type="button" onClick={onDisconnectAi} className="w-fit rounded-xl border border-line-strong px-4 py-2 text-sm text-muted hover:text-ink">{t('ai.disconnect')}</button>
                </div>
              ) : (
                <div className="grid gap-3">
                  <button type="button" onClick={onConnectAi} disabled={ai.checking}
                    className="w-fit rounded-xl px-4 py-2 text-sm font-semibold transition hover:brightness-110 disabled:opacity-60"
                    style={{ color: '#d8b4fe', background: 'rgb(139 92 246 / .14)', border: '1px solid rgb(139 92 246 / .45)' }}>
                    {ai.checking ? t('ai.checking') : t('ai.connect')}
                  </button>
                  {ai.status?.state === 'not_installed' && (
                    <p className="text-sm text-caution" role="status">
                      {t('ai.notInstalled')}{' '}
                      <a className="underline" href="https://code.claude.com/docs/en/quickstart" target="_blank" rel="noreferrer noopener">{t('ai.installHow')}</a>
                    </p>
                  )}
                  {ai.status?.state === 'not_logged_in' && <p className="text-sm text-caution" role="status">{t('ai.notLoggedIn')}</p>}
                  {ai.error && <p className="text-sm text-caution" role="alert">{ai.error}</p>}
                </div>
              )}
              <p className="text-xs leading-relaxed text-dim">{t('ai.privacy')}</p>
            </section>

            <section className="grid gap-2 border-t border-line pt-5" data-testid="about">
              <h3 className="font-medium">{t('about.title')}</h3>
              <p className="font-mono text-xs text-muted">{t('about.ui')}: {UI_BUILD}</p>
              <p className="font-mono text-xs text-muted">{t('about.engine')}: {engine && engine.build !== 'unknown' ? `${engine.version} (${engine.build})` : t('about.unknown')}</p>
              {buildsDiffer(UI_BUILD, engine?.build) && <p className="text-xs text-caution" role="alert">{t('about.mismatch')}</p>}
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
