import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import { detectLang, translate, type UiKey } from './ui'
import type { Lang } from './types'

interface LangContextValue {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: UiKey) => string
}

const LangContext = createContext<LangContextValue | null>(null)
const STORAGE_KEY = 'apkguard.lang'

function initialLang(): Lang {
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY)
    if (stored === 'it' || stored === 'en') return stored
  } catch {
    /* storage unavailable */
  }
  return detectLang(typeof navigator === 'undefined' ? undefined : navigator.language)
}

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(initialLang)

  const setLang = useCallback((next: Lang) => {
    setLangState(next)
    document.documentElement.lang = next
    try {
      window.localStorage.setItem(STORAGE_KEY, next)
    } catch {
      /* not persisted */
    }
  }, [])

  const value = useMemo<LangContextValue>(
    () => ({ lang, setLang, t: (key) => translate(lang, key) }),
    [lang, setLang],
  )
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}

export function useLang(): LangContextValue {
  const ctx = useContext(LangContext)
  if (!ctx) throw new Error('useLang must be used inside LangProvider')
  return ctx
}
