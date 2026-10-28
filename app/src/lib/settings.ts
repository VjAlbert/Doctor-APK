import type { KeyValueStore } from './history'

export interface Settings {
  vtEnabled: boolean
  vtKey: string
}

const KEY = 'apkguard.settings'
export const DEFAULT_SETTINGS: Settings = { vtEnabled: false, vtKey: '' }
/** VirusTotal keys are 64 hex characters; the engine accepts 16-128 alphanumerics. */
export const VT_KEY_PATTERN = /^[A-Za-z0-9]{16,128}$/

function browserStore(): KeyValueStore | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

export function loadSettings(store: KeyValueStore | null = browserStore()): Settings {
  try {
    const raw = JSON.parse(store?.getItem(KEY) ?? '{}')
    return {
      vtEnabled: raw.vtEnabled === true,
      vtKey: typeof raw.vtKey === 'string' ? raw.vtKey : '',
    }
  } catch {
    return DEFAULT_SETTINGS
  }
}

export function saveSettings(settings: Settings, store: KeyValueStore | null = browserStore()): void {
  try {
    store?.setItem(KEY, JSON.stringify(settings))
  } catch {
    /* not persisted */
  }
}

/** The key to send with an analysis: only when the check is on and the key looks valid. */
export function activeVtKey(settings: Settings): string | undefined {
  const key = settings.vtKey.trim()
  return settings.vtEnabled && VT_KEY_PATTERN.test(key) ? key : undefined
}
