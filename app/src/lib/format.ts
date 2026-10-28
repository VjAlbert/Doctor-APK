import type { Lang } from './types'

export function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  const units = ['KB', 'MB', 'GB']
  let value = bytes / 1024
  let unit = 0
  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024
    unit += 1
  }
  return `${value.toFixed(value >= 100 ? 0 : 1)} ${units[unit]}`
}

export function shortHash(hash: string, size = 8): string {
  return hash.length > size * 2 ? `${hash.slice(0, size)}…${hash.slice(-size)}` : hash
}

export function timeAgo(timestamp: number, lang: Lang, now = Date.now()): string {
  const seconds = Math.max(0, Math.round((now - timestamp) / 1000))
  const rtf = new Intl.RelativeTimeFormat(lang, { numeric: 'auto' })
  if (seconds < 60) return rtf.format(0, 'second')
  if (seconds < 3600) return rtf.format(-Math.round(seconds / 60), 'minute')
  if (seconds < 86400) return rtf.format(-Math.round(seconds / 3600), 'hour')
  return rtf.format(-Math.round(seconds / 86400), 'day')
}

/** Renders a finding parameter for the technical view. */
export function formatParam(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join(', ')
  if (value !== null && typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
