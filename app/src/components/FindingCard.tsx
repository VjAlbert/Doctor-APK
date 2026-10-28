import { AnimatePresence, motion } from 'framer-motion'
import { useState } from 'react'
import { formatParam } from '../lib/format'
import { useLang } from '../lib/lang'
import { SEVERITY_COLOR } from '../lib/severity'
import type { Finding } from '../lib/types'
import { ChevronIcon } from './Icons'
import { SeverityBadge } from './SeverityBadge'

interface Props {
  finding: Finding
  technical: boolean
  defaultOpen?: boolean
}

export function FindingCard({ finding, technical, defaultOpen = false }: Props) {
  const { t } = useLang()
  const [open, setOpen] = useState(defaultOpen)
  const color = SEVERITY_COLOR[finding.severity]
  const { text } = finding
  const params = Object.entries(finding.params).filter(([k]) => k !== 'category')

  return (
    <article className="glass overflow-hidden rounded-2xl" style={{ borderLeft: `3px solid ${color}` }} data-severity={finding.severity}>
      <button type="button" onClick={() => setOpen((v) => !v)} aria-expanded={open}
        className="flex w-full items-start gap-4 px-5 py-4 text-left">
        <div className="min-w-0 flex-1">
          <div className="mb-1.5 flex flex-wrap items-center gap-2"><SeverityBadge severity={finding.severity} /></div>
          <h3 className="text-[15px] font-semibold leading-snug">{text.title}</h3>
          {!open && <p className="mt-1 line-clamp-1 text-sm text-muted">{text.description}</p>}
        </div>
        <motion.span animate={{ rotate: open ? 180 : 0 }} className="mt-1 text-dim"><ChevronIcon size={18} /></motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }} exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }} className="overflow-hidden">
            <div className="grid gap-4 border-t border-line px-5 py-4 text-sm">
              <section>
                <h4 className="mb-1 font-mono text-[10.5px] uppercase tracking-[0.18em] text-dim">{t('threats.what')}</h4>
                <p className="leading-relaxed text-ink/90">{text.description}</p>
                {text.note && <p className="mt-2 text-xs text-muted">{text.note}</p>}
              </section>
              {text.advice && (
                <section>
                  <h4 className="mb-1 font-mono text-[10.5px] uppercase tracking-[0.18em] text-dim">{t('threats.advice')}</h4>
                  <p className="leading-relaxed text-ink/90">{text.advice}</p>
                </section>
              )}
              {technical && (
                <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 rounded-xl bg-black/30 p-3 font-mono text-[12px]" data-testid="technical">
                  <dt className="text-dim">{t('threats.id')}</dt><dd className="break-all text-cyan">{finding.id}</dd>
                  <dt className="text-dim">{t('threats.module')}</dt><dd>{finding.module}</dd>
                  {params.map(([key, value]) => (
                    <div key={key} className="contents"><dt className="text-dim">{key}</dt><dd className="break-all">{formatParam(value)}</dd></div>
                  ))}
                </dl>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </article>
  )
}
