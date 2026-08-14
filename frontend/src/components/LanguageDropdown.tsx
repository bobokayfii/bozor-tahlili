import { useEffect, useRef, useState } from 'react'
import { useLanguage } from '../lib/LanguageContext'
import type { Lang } from '../lib/i18n'
import uzFlag from '../assets/flags/uz.svg'
import ruFlag from '../assets/flags/ru.svg'

const LANG_CODES: Record<Lang, string> = {
  uz: 'UZ',
  ru: 'RU',
}

// Bayroqlar Unicode regional-indicator emoji (🇺🇿/🇷🇺) o'rniga SVG sifatida
// saqlangan — Windows'dagi ko'plab Chrome versiyalari bu emoji juftligini
// haqiqiy bayroq belgisi sifatida emas, balki oddiy ikki harfli kod
// ("UZ"/"RU") sifatida ko'rsatadi (shrift darajasidagi cheklov, brauzer
// xatosi emas), shu sabab har doim bir xil ko'rinishni kafolatlaydigan SVG
// tanlandi.
const LANG_FLAGS: Record<Lang, string> = {
  uz: uzFlag,
  ru: ruFlag,
}

export function LanguageDropdown() {
  const { lang, setLang, t } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!isOpen) return

    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [isOpen])

  function handleSelect(next: Lang) {
    setLang(next)
    setIsOpen(false)
  }

  return (
    <div className="lang-dropdown" ref={containerRef}>
      <button
        type="button"
        className="lang-dropdown-btn"
        aria-label={t('langToggleLabel')}
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
      >
        <img src={LANG_FLAGS[lang]} alt="" className="lang-flag-icon" />
        {LANG_CODES[lang]}
        <span className={isOpen ? 'export-btn-caret export-btn-caret-open' : 'export-btn-caret'} aria-hidden="true">
          ▾
        </span>
      </button>
      {isOpen && (
        <div className="lang-dropdown-panel" role="menu">
          {(Object.keys(LANG_CODES) as Lang[]).map((option) => (
            <button
              key={option}
              type="button"
              role="menuitemradio"
              aria-checked={lang === option}
              className={lang === option ? 'lang-dropdown-item lang-dropdown-item-active' : 'lang-dropdown-item'}
              onClick={() => handleSelect(option)}
            >
              <img src={LANG_FLAGS[option]} alt="" className="lang-flag-icon" />
              {t(option === 'uz' ? 'langOptionUz' : 'langOptionRu')}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
