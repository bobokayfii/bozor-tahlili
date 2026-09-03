import { useEffect, useState } from 'react'
import { fetchScrapeRuns } from '../lib/api'
import { getBankLogo } from '../lib/bankLogos'
import { useLanguage } from '../lib/LanguageContext'
import type { ScrapeRun, ScrapeRunStatus } from '../lib/types'

function formatRunTime(iso: string | null, lang: 'uz' | 'ru'): string {
  if (!iso) return '-'
  const locale = lang === 'ru' ? 'ru-RU' : 'uz-UZ'
  return new Date(iso).toLocaleString(locale, { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

// ScrapeRunRow allaqachon bazaga har bir bank uchun har bir scrape
// urinishining natijasini (muvaffaqiyatli/xato/sababi) yozib boradi, lekin
// bu ma'lumot hech qayerda ko'rsatilmas edi — bank sayti o'zgarib scraper
// jim-jit ishlamay qolsa, hech kim buni bilmasdi, sayt esa shu bankning
// eskirgan ma'lumotini "hammasi joyida" ko'rinishida ko'rsatishda davom
// etaverardi. Bu panel shu bo'shliqni yopadi.
export function ScrapeStatusPanel() {
  const { lang, t } = useLanguage()
  const [runs, setRuns] = useState<ScrapeRun[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState<{ message: string | null } | null>(null)

  useEffect(() => {
    async function loadRuns() {
      setIsLoading(true)
      try {
        const data = await fetchScrapeRuns()
        setRuns(data)
        setLoadError(null)
      } catch (err) {
        setLoadError({ message: err instanceof Error ? err.message : null })
      } finally {
        setIsLoading(false)
      }
    }
    loadRuns()
  }, [])

  function statusLabel(status: ScrapeRunStatus): string {
    switch (status) {
      case 'success':
        return t('scrapeStatusSuccess')
      case 'failed':
        return t('scrapeStatusFailed')
      case 'running':
        return t('scrapeStatusRunning')
      case 'no_products':
        return t('scrapeStatusNoProducts')
      default:
        return t('scrapeStatusNeverRun')
    }
  }

  return (
    <div className="scrape-status-panel">
      <div className="page-head">
        <div>
          <h1>{t('scrapeStatusTitle')}</h1>
          <p className="page-subtitle">{t('scrapeStatusSubtitle')}</p>
        </div>
      </div>

      {loadError && <p className="error-state">{loadError.message ?? t('scrapeStatusLoadFailed')}</p>}

      {!isLoading && (
        <div className="scrape-status-board rate-board">
          <div className="rate-board-head">
            <span>{t('tableBank')}</span>
            <span>{t('scrapeColStatus')}</span>
            <span>{t('scrapeColLastRun')}</span>
            <span>{t('scrapeColProductsFound')}</span>
          </div>
          {runs
            .filter((run) => run.status !== 'no_products')
            .map((run) => (
              <div className="rate-row" key={run.bank}>
                <span className="rate-bank">
                  {getBankLogo(run.bank) && <img src={getBankLogo(run.bank)} alt="" className="rate-bank-logo" />}
                  <span className="rate-bank-name">{run.bank}</span>
                </span>
                <span>
                  <span className={`scrape-status-badge scrape-status-badge-${run.status}`}>
                    {statusLabel(run.status)}
                  </span>
                </span>
                <span className="rate-term">{formatRunTime(run.finished_at ?? run.started_at, lang)}</span>
                <span className="rate-term">{run.status === 'success' ? run.products_found : '-'}</span>
                {run.status === 'failed' && run.error_message && (
                  <span className="scrape-error-message" style={{ gridColumn: '1 / -1' }}>
                    {run.error_message}
                  </span>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  )
}
