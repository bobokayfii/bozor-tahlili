import { useEffect, useRef, useState } from 'react'
import { downloadFile, getExportAllExcelUrl, getExportExcelUrl } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { DownloadIcon } from './icons'

interface ExportMenuProps {
  category: string | null
}

export function ExportMenu({ category }: ExportMenuProps) {
  const { lang, t } = useLanguage()
  const [isOpen, setIsOpen] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)
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

  async function handleExportCurrent() {
    setIsOpen(false)
    try {
      await downloadFile(getExportExcelUrl(category as string, lang), `${category}.xlsx`)
    } catch {
      setExportError(t('exportFailed'))
    }
  }

  async function handleExportAll() {
    setIsOpen(false)
    try {
      await downloadFile(getExportAllExcelUrl(lang), 'bozor-tahlili-barcha-kategoriyalar.xlsx')
    } catch {
      setExportError(t('exportFailed'))
    }
  }

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
          <button type="button" className="export-menu-item" role="menuitem" onClick={handleExportCurrent}>
            {t('exportCurrentPage')}
          </button>
          <button type="button" className="export-menu-item" role="menuitem" onClick={handleExportAll}>
            {t('exportAllCategories')}
          </button>
        </div>
      )}

      {exportError && (
        <div className="refresh-status refresh-status-error" role="status">
          <span>{exportError}</span>
          <button
            type="button"
            className="refresh-status-close"
            aria-label={t('closeLabel')}
            onClick={() => setExportError(null)}
          >
            ×
          </button>
        </div>
      )}
    </div>
  )
}
