import { motion } from 'framer-motion'
import { formatSize, shortHash } from '../lib/format'
import { useLang } from '../lib/lang'
import { LEVEL_COLOR, SEVERITY_COLOR } from '../lib/severity'
import { severityKey, type UiKey } from '../lib/ui'
import { SEVERITIES, type Report, type VerdictId } from '../lib/types'
import { AlertIcon, ArrowLeftIcon, BlockIcon, InfoIcon, ShieldIcon } from './Icons'
import { Gauge } from './Gauge'
import { SeverityBadge } from './SeverityBadge'

const ICON: Record<VerdictId, typeof ShieldIcon> = {
  no_known_threats: ShieldIcon,
  caution: AlertIcon,
  do_not_install: BlockIcon,
}

interface Props {
  report: Report
  onViewAll: () => void
  onAnother: () => void
}

export function VerdictView({ report, onViewAll, onAnother }: Props) {
  const { t } = useLang()
  const { verdict, app, file, authenticity } = report
  const color = LEVEL_COLOR[verdict.level]
  const Icon = ICON[verdict.id]
  const total = Object.entries(verdict.counts).filter(([k]) => k !== 'info').reduce((n, [, v]) => n + v, 0)

  const facts: [string, string][] = [
    [t('verdict.package'), app.package],
    [t('verdict.version'), app.version_name ?? '—'],
    [t('verdict.category'), verdict.text.category],
    [t('verdict.signature'), authenticity.label],
    [t('verdict.size'), formatSize(file.size)],
    [t('verdict.online'), t(`rep.${report.reputation.status === 'known' ? 'known' : report.reputation.status}` as UiKey)],
    [t('verdict.hash'), shortHash(file.sha256, 6)],
  ]

  return (
    <div className="mx-auto w-full max-w-5xl">
      <div className="grid gap-6 md:grid-cols-[minmax(0,330px)_1fr]">
        <motion.section initial={{ opacity: 0, scale: 0.96 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.5 }}
          className="glass flex flex-col gap-5 self-start rounded-3xl p-6" style={{ boxShadow: `0 0 80px -30px ${color}77, 0 20px 50px -20px #000` }}>
          <Gauge score={verdict.score} level={verdict.level} label={t('verdict.risk')} />
          <ul className="flex flex-wrap justify-center gap-2" aria-label={t('threats.title')}>
            {SEVERITIES.filter((s) => s !== 'info' && verdict.counts[s] > 0).map((s) => (
              <li key={s} className="flex items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-xs"
                style={{ color: SEVERITY_COLOR[s], background: `${SEVERITY_COLOR[s]}18`, border: `1px solid ${SEVERITY_COLOR[s]}40` }}>
                {verdict.counts[s]} {t(severityKey(s))}
              </li>
            ))}
          </ul>
        </motion.section>

        <section className="flex min-w-0 flex-col gap-5">
          <motion.header initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className="flex items-center gap-3" style={{ color }}>
              <Icon size={30} />
              <h1 className="text-3xl font-semibold tracking-tight" data-testid="verdict-title">{verdict.text.title}</h1>
            </div>
            <p className="mt-2 max-w-xl text-[15px] leading-relaxed text-muted">{verdict.text.summary}</p>
            <p className="mt-3 flex items-start gap-2 text-xs leading-relaxed text-dim">
              <InfoIcon size={14} className="mt-0.5 shrink-0" />{verdict.text.limitations}
            </p>
          </motion.header>

          <div>
            <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('verdict.why')}</h2>
            {verdict.reasons.length === 0 ? (
              <p className="glass rounded-2xl px-5 py-4 text-sm text-muted">{t('verdict.nothing')}</p>
            ) : (
              <ul className="grid gap-2.5">
                {verdict.reasons.map((reason, i) => (
                  <motion.li key={`${reason.id}-${i}`} initial={{ opacity: 0, x: 16 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.25 + i * 0.12 }} className="glass rounded-2xl px-5 py-3.5"
                    style={{ borderLeft: `3px solid ${SEVERITY_COLOR[reason.severity]}` }}>
                    <div className="mb-1 flex items-center gap-2"><SeverityBadge severity={reason.severity} /></div>
                    <p className="font-semibold leading-snug">{reason.text.title}</p>
                    <p className="mt-0.5 line-clamp-2 text-sm text-muted">{reason.text.description}</p>
                  </motion.li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap gap-3">
            <button type="button" onClick={onViewAll}
              className="rounded-xl px-5 py-2.5 text-sm font-semibold text-bg transition hover:brightness-110"
              style={{ background: 'linear-gradient(135deg, #22d3ee, #67e8f9)', boxShadow: '0 8px 30px -8px #22d3ee99' }}>
              {t('verdict.viewAll')} ({total})
            </button>
            <button type="button" onClick={onAnother}
              className="flex items-center gap-2 rounded-xl border border-line-strong px-5 py-2.5 text-sm font-medium text-ink transition hover:bg-white/[.04]">
              <ArrowLeftIcon size={16} />{t('verdict.another')}
            </button>
          </div>
        </section>
      </div>

      <motion.dl initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.5 }}
        className="glass mt-6 grid grid-cols-2 gap-x-6 gap-y-4 rounded-2xl px-6 py-5 md:grid-cols-3 lg:grid-cols-4">
        {facts.map(([label, value]) => (
          <div key={label} className="min-w-0">
            <dt className="font-mono text-[10.5px] uppercase tracking-[0.16em] text-dim">{label}</dt>
            <dd className="mt-1 truncate text-sm" title={value}>{value}</dd>
          </div>
        ))}
      </motion.dl>
    </div>
  )
}
