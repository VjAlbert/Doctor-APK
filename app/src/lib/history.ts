import type { Report } from './types'

export interface HistoryEntry {
  id: string
  savedAt: number
  report: Report
}

export interface KeyValueStore {
  getItem(key: string): string | null
  setItem(key: string, value: string): void
  removeItem(key: string): void
}

const KEY = 'apkguard.history'
export const MAX_ENTRIES = 10

function browserStore(): KeyValueStore | null {
  try {
    return window.localStorage
  } catch {
    return null // blocked storage: the app works, it just does not remember
  }
}

export function loadHistory(store: KeyValueStore | null = browserStore()): HistoryEntry[] {
  if (!store) return []
  try {
    const parsed = JSON.parse(store.getItem(KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter((e) => e?.report?.verdict) : []
  } catch {
    return []
  }
}

/** Adds an entry (newest first), de-duplicating by file hash. Returns the new list. */
export function addToHistory(
  report: Report,
  store: KeyValueStore | null = browserStore(),
  now = Date.now(),
): HistoryEntry[] {
  const entry: HistoryEntry = { id: `${report.file.sha256}-${now}`, savedAt: now, report }
  const rest = loadHistory(store).filter((e) => e.report.file.sha256 !== report.file.sha256)
  const next = [entry, ...rest].slice(0, MAX_ENTRIES)
  try {
    store?.setItem(KEY, JSON.stringify(next))
  } catch {
    /* quota exceeded: keep the in-memory list only */
  }
  return next
}

export function clearHistory(store: KeyValueStore | null = browserStore()): void {
  try {
    store?.removeItem(KEY)
  } catch {
    /* nothing to do */
  }
}
