import { motion, useReducedMotion } from 'framer-motion'

const BLIPS = [
  [58, -34], [-62, 20], [24, 70], [-30, -66], [84, 38], [-82, -24], [10, -88], [-12, 88], [70, -70],
] as const

export function Radar({ progress }: { progress: number }) {
  const reduced = useReducedMotion()
  return (
    <svg viewBox="-110 -110 220 220" className="size-full" role="img" aria-label="radar">
      <defs>
        <radialGradient id="radar-bg"><stop offset="0" stopColor="#22d3ee" stopOpacity=".14" /><stop offset="1" stopColor="#22d3ee" stopOpacity="0" /></radialGradient>
        <linearGradient id="sweep" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stopColor="#22d3ee" stopOpacity="0" /><stop offset="1" stopColor="#22d3ee" stopOpacity=".55" /></linearGradient>
      </defs>
      <circle r="104" fill="url(#radar-bg)" />
      {[104, 78, 52, 26].map((r) => <circle key={r} r={r} fill="none" stroke="#22d3ee" strokeOpacity=".22" />)}
      <path d="M-104 0H104M0-104V104" stroke="#22d3ee" strokeOpacity=".16" />
      <motion.g animate={reduced ? undefined : { rotate: 360 }} transition={{ repeat: Infinity, duration: 3.2, ease: 'linear' }}>
        <path d="M0 0 L104 0 A104 104 0 0 0 76 -71 Z" fill="url(#sweep)" />
        <path d="M0 0H104" stroke="#67e8f9" strokeWidth="1.5" />
      </motion.g>
      {BLIPS.map(([x, y], i) => (
        <motion.circle key={i} cx={x} cy={y} r="3.2" fill="#67e8f9"
          initial={{ opacity: 0, scale: 0 }}
          animate={{ opacity: i < progress ? 1 : 0, scale: i < progress ? 1 : 0 }}
          style={{ filter: 'drop-shadow(0 0 5px #22d3ee)' }} />
      ))}
      <circle r="3" fill="#22d3ee" />
    </svg>
  )
}
