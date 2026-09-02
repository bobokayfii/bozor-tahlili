import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { translate, type Lang, type TranslationKey } from './i18n'

const STORAGE_KEY = 'bozor-tahlili-lang'

interface LanguageContextValue {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: TranslationKey) => string
}

const LanguageContext = createContext<LanguageContextValue | null>(null)

function readStoredLang(): Lang {
  if (typeof window === 'undefined') return 'uz'
  const stored = window.localStorage.getItem(STORAGE_KEY)
  return stored === 'ru' ? 'ru' : 'uz'
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(readStoredLang)

  useEffect(() => {
    window.localStorage.setItem(STORAGE_KEY, lang)
  }, [lang])

  const value = useMemo<LanguageContextValue>(
    () => ({ lang, setLang, t: (key: TranslationKey) => translate(lang, key) }),
    [lang],
  )

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>
}

// Colocated with LanguageProvider so callers have one import path; costs only
// Vite's Fast Refresh doing a full reload instead of a component-only one
// when this file changes, which doesn't justify splitting a one-line hook
// into its own file.
// eslint-disable-next-line react-refresh/only-export-components
export function useLanguage(): LanguageContextValue {
  const context = useContext(LanguageContext)
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider')
  }
  return context
}
