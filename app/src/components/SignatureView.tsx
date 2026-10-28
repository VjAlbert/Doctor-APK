import { useState } from 'react'
import { closestExpected, diffFingerprint, groupHex } from '../lib/fingerprint'
import { useLang } from '../lib/lang'
import type { UiKey } from '../lib/ui'
import type { Report } from '../lib/types'
import { CheckIcon, CopyIcon } from './Icons'

const STATUS_COLOR: Record<string, string> = {
  match: '#34d399', other_channel: '#fbbf24', mismatch: '#ff3b6b', unknown: '#8a9bb2', unsigned: '#ff7a45',
}

function CopyButton({ value }: { value: string }) {
  const { t } = useLang()
  const [done, setDone] = useState(false)
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value)
      setDone(true)
      setTimeout(() => setDone(false), 1500)
    } catch {
      /* clipboard unavailable: nothing to do */
    }
  }
  return (
    <button type="button" onClick={() => void copy()} className="flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-dim transition hover:text-ink">
      {done ? <CheckIcon size={13} /> : <CopyIcon size={13} />}{done ? t('sig.copied') : t('sig.copy')}
    </button>
  )
}

function Fingerprint({ hex, diff }: { hex: string; diff?: { text: string; same: boolean }[] }) {
  const groups = diff ?? groupHex(hex).map((text) => ({ text, same: true }))
  return (
    <p className="flex flex-wrap gap-x-2.5 gap-y-1 font-mono text-[13px]" data-testid="fingerprint">
      {groups.map((g, i) => (
        <span key={i} style={diff ? { color: g.same ? '#34d399' : '#ff5c5c', fontWeight: g.same ? 400 : 600 } : undefined}>{g.text}</span>
      ))}
    </p>
  )
}

export function SignatureView({ report }: { report: Report }) {
  const { t } = useLang()
  const { authenticity, certificates } = report
  const color = STATUS_COLOR[authenticity.status] ?? '#8a9bb2'
  const explain = t(`sig.explain.${authenticity.status}` as UiKey).replace('{sources}', authenticity.sources.join(', '))
  const found = certificates[0]?.sha256
  const expected = authenticity.expected
  const closest = found && expected.length ? expected[closestExpected(found, expected.map((e) => e.sha256))] : undefined
  const same = found && closest ? diffFingerprint(found, closest.sha256).filter((g) => g.same).length : 0

  return (
    <div className="scroll mx-auto h-full w-full max-w-4xl overflow-y-auto pb-8 pr-2">
      <h1 className="text-2xl font-semibold tracking-tight">{t('sig.title')}</h1>

      <section className="glass mt-5 rounded-2xl p-5" style={{ borderLeft: `3px solid ${color}` }}>
        <p className="text-lg font-semibold" style={{ color }}>{authenticity.label}</p>
        <p className="mt-1 text-sm leading-relaxed text-muted">{explain}</p>
      </section>

      {found && (
        <section className="glass mt-5 rounded-2xl p-5">
          <h2 className="mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('sig.compare')}</h2>
          {closest ? (
            <div className="grid gap-4">
              <div>
                <p className="mb-1 flex items-center gap-2 text-xs text-dim">{t('sig.expected')} · {closest.source}</p>
                <Fingerprint hex={closest.sha256} />
              </div>
              <div>
                <p className="mb-1 flex items-center gap-3 text-xs text-dim">
                  {t('sig.found')}<span className="font-mono">{same}/{groupHex(found).length} {t('sig.sameGroups')}</span>
                </p>
                <Fingerprint hex={found} diff={diffFingerprint(found, closest.sha256)} />
              </div>
            </div>
          ) : (
            <div>
              <p className="mb-2 text-sm text-muted">{t('sig.noExpected')}</p>
              <p className="mb-1 text-xs text-dim">{t('sig.found')}</p>
              <Fingerprint hex={found} />
            </div>
          )}
        </section>
      )}

      {certificates.length > 0 && (
        <section className="mt-5">
          <h2 className="mb-2.5 font-mono text-[11px] uppercase tracking-[0.18em] text-muted">{t('sig.certificates')}</h2>
          <ul className="grid gap-2.5">
            {certificates.map((cert) => (
              <li key={cert.sha256} className="glass rounded-2xl p-5 text-sm">
                <dl className="grid grid-cols-[auto_1fr] gap-x-5 gap-y-1.5">
                  <dt className="text-dim">{t('sig.subject')}</dt><dd className="break-words">{cert.subject}</dd>
                  <dt className="text-dim">{t('sig.issuer')}</dt><dd className="break-words">{cert.issuer}</dd>
                  <dt className="text-dim">{t('sig.validUntil')}</dt><dd>{cert.not_after.slice(0, 10)}</dd>
                  <dt className="text-dim">SHA-256</dt>
                  <dd className="flex flex-wrap items-center gap-2 font-mono text-xs"><span className="break-all">{cert.sha256}</span><CopyButton value={cert.sha256} /></dd>
                </dl>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  )
}
