import { motion } from 'framer-motion'
import { useLang } from '../lib/lang'
import type { UiKey } from '../lib/ui'

export type ResultView = 'verdict' | 'threats' | 'permissions' | 'signature'

const TABS: { id: ResultView; label: UiKey }[] = [
  { id: 'verdict', label: 'tab.summary' },
  { id: 'threats', label: 'tab.findings' },
  { id: 'permissions', label: 'tab.permissions' },
  { id: 'signature', label: 'tab.signature' },
]

export function Tabs({ view, onChange }: { view: ResultView; onChange: (view: ResultView) => void }) {
  const { t } = useLang()
  return (
    <div role="tablist" className="glass relative flex rounded-xl p-1">
      {TABS.map((tab) => {
        const active = view === tab.id
        return (
          <button key={tab.id} type="button" role="tab" aria-selected={active} onClick={() => onChange(tab.id)}
            className="relative rounded-lg px-4 py-1.5 text-sm font-medium transition"
            style={{ color: active ? '#e6edf6' : '#8a9bb2' }}>
            {active && (
              <motion.span layoutId="tab-pill" className="absolute inset-0 rounded-lg"
                style={{ background: 'rgb(34 211 238 / .14)', border: '1px solid rgb(34 211 238 / .35)' }}
                transition={{ type: 'spring', stiffness: 400, damping: 32 }} />
            )}
            <span className="relative">{t(tab.label)}</span>
          </button>
        )
      })}
    </div>
  )
}
