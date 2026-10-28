import { animate, motion } from 'framer-motion'
import { useEffect, useState } from 'react'
import { LEVEL_COLOR } from '../lib/severity'
import type { RiskLevel } from '../lib/types'

const CX = 110, CY = 110, R = 90, START = 135, SWEEP = 270

function polar(angle: number) {
  const rad = (angle * Math.PI) / 180
  return [CX + R * Math.cos(rad), CY + R * Math.sin(rad)] as const
}

const [x1, y1] = polar(START)
const [x2, y2] = polar(START + SWEEP)
const TRACK = `M ${x1} ${y1} A ${R} ${R} 0 1 1 ${x2} ${y2}`

export function Gauge({ score, level, label }: { score: number; level: RiskLevel; label: string }) {
  const color = LEVEL_COLOR[level]
  const [shown, setShown] = useState(0)

  useEffect(() => {
    const controls = animate(0, score, { duration: 1.5, ease: [0.16, 1, 0.3, 1], onUpdate: (v) => setShown(Math.round(v)) })
    return () => controls.stop()
  }, [score])

  return (
    <div className="relative mx-auto aspect-square w-full max-w-[300px]" role="img" aria-label={`${label}: ${score}/100`}>
      <svg viewBox="0 0 220 220" className="size-full overflow-visible">
        <defs>
          <linearGradient id="gauge-fill" x1="0" y1="1" x2="1" y2="0">
            <stop offset="0" stopColor={color} stopOpacity=".55" /><stop offset="1" stopColor={color} />
          </linearGradient>
        </defs>
        {Array.from({ length: 28 }, (_, i) => {
          const a = START + (SWEEP * i) / 27
          const rad = (a * Math.PI) / 180
          const r1 = R + 12, r2 = R + (i % 9 === 0 ? 20 : 16)
          return <line key={i} x1={CX + r1 * Math.cos(rad)} y1={CY + r1 * Math.sin(rad)}
            x2={CX + r2 * Math.cos(rad)} y2={CY + r2 * Math.sin(rad)} stroke="#8a9bb2" strokeOpacity=".35" strokeWidth="1.2" />
        })}
        <path d={TRACK} fill="none" stroke="#ffffff" strokeOpacity=".07" strokeWidth="14" strokeLinecap="round" />
        <motion.path d={TRACK} fill="none" stroke="url(#gauge-fill)" strokeWidth="14" strokeLinecap="round"
          initial={{ pathLength: 0 }} animate={{ pathLength: Math.max(score, 1.5) / 100 }}
          transition={{ duration: 1.5, ease: [0.16, 1, 0.3, 1] }}
          style={{ filter: `drop-shadow(0 0 10px ${color}99)` }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center pt-2">
        <span className="font-mono text-6xl font-semibold tabular-nums leading-none" style={{ color, textShadow: `0 0 28px ${color}66` }}>
          {shown}
        </span>
        <span className="mt-2 font-mono text-[11px] uppercase tracking-[0.25em] text-muted">{label}</span>
      </div>
    </div>
  )
}
