import { motion } from 'framer-motion'
import { useLang } from '../lib/lang'
import { moduleKey } from '../lib/ui'
import { MODULES } from '../lib/types'
import { CheckIcon, FileIcon } from './Icons'
import { Radar } from './Radar'

export function ScanView({ fileName, shown }: { fileName: string; shown: number }) {
  const { t } = useLang()
  const percent = Math.round((shown / MODULES.length) * 100)
  return (
    <div className="mx-auto grid w-full max-w-4xl items-center gap-10 md:grid-cols-[minmax(0,320px)_1fr]">
      <div className="relative mx-auto aspect-square w-full max-w-[320px]">
        <Radar progress={shown} />
      </div>
      <div>
        <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-cyan">{t('scan.subtitle')}</p>
        <h2 className="mt-1 text-3xl font-semibold tracking-tight">{t('scan.title')}<span className="text-cyan">…</span></h2>
        <p className="mt-3 flex items-center gap-2 text-sm text-muted">
          <FileIcon size={16} /><span className="truncate font-mono">{fileName}</span>
        </p>
        <div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/[.06]" role="progressbar"
          aria-valuemin={0} aria-valuemax={100} aria-valuenow={percent}>
          <motion.div className="h-full rounded-full" animate={{ width: `${percent}%` }}
            transition={{ type: 'spring', stiffness: 120, damping: 20 }}
            style={{ background: 'linear-gradient(90deg, #22d3ee, #8b5cf6)', boxShadow: '0 0 14px #22d3ee' }} />
        </div>
        <ol className="mt-6 grid gap-2" aria-live="polite">
          {MODULES.map((module, i) => {
            const done = i < shown
            const active = i === shown
            return (
              <li key={module} className="flex items-center gap-3 text-sm"
                style={{ opacity: done || active ? 1 : 0.38, transition: 'opacity .3s' }}>
                <span className="grid size-5 place-items-center rounded-full"
                  style={{ border: `1px solid ${done ? '#34d399' : active ? '#22d3ee' : 'rgb(148 197 255 / .25)'}`,
                           background: done ? 'rgb(52 211 153 / .15)' : 'transparent',
                           color: '#34d399' }}>
                  {done ? <CheckIcon size={12} strokeWidth={3} /> : active ? (
                    <motion.span className="size-2 rounded-full bg-cyan" animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ repeat: Infinity, duration: 0.9 }} />
                  ) : null}
                </span>
                <span className={done ? 'text-ink' : active ? 'text-ink' : 'text-muted'}>{t(moduleKey(module))}</span>
              </li>
            )
          })}
        </ol>
      </div>
    </div>
  )
}
