import { useEffect, useRef, useState } from 'react'
import { getExportAllExcelUrl, getExportExcelUrl } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { DownloadIcon } from './icons'

interface ExportMenuProps {
  category: string | null
}

// Oddiy <a href> yetarli: bu GET so'rovlar autentifikatsiyasiz, backend
// Content-Disposition: attachment sarlavhasini qaytaradi, brauzer o'zi
// yuklab olishni boshlaydi — fetch/blob orqali qo'lda yuklash shart emas.
export function ExportMenu({ category }: ExportMenuProps) {
  const { lang, t } = useLanguage()
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

  if (!category) return null

  return (
    <div className="export-menu" ref={containerRef}>
      <button type="button" className="export-btn" onClick={() => setIsOpen((prev) => !prev)}>
        <DownloadIcon />
        {t('exportButton')}
        <span className={isOpen ? 'export-btn-caret export-btn-caret-open' : 'export-btn-caret'} aria-hidden="true">
          ▾
        </span>
      </button>
      {isOpen && (
        <div className="export-menu-panel" role="menu">
          <a
            className="export-menu-item"
            role="menuitem"
            href={getExportExcelUrl(category, lang)}
            onClick={() => setIsOpen(false)}
          >
            {t('exportCurrentPage')}
          </a>
          <a
            className="export-menu-item"
            role="menuitem"
            href={getExportAllExcelUrl(lang)}
            onClick={() => setIsOpen(false)}
          >
            {t('exportAllCategories')}
          </a>
        </div>
      )}
    </div>
  )
}
