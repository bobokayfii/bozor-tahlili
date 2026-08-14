import { useState } from 'react'
import { triggerScrapeRefresh } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { RefreshIcon } from './icons'

type StatusMessage = { kind: 'success' | 'warning' | 'error'; text: string } | null

export function RefreshDataButton() {
  const { t } = useLanguage()
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<StatusMessage>(null)

  async function handleConfirm() {
    setIsConfirmOpen(false)
    setIsSubmitting(true)
    try {
      const result = await triggerScrapeRefresh()
      if (result === 'started') {
        setStatusMessage({ kind: 'success', text: t('refreshStarted') })
      } else if (result === 'already_running') {
        setStatusMessage({ kind: 'warning', text: t('refreshAlreadyRunning') })
      } else {
        setStatusMessage({ kind: 'error', text: t('refreshFailed') })
      }
    } catch {
      setStatusMessage({ kind: 'error', text: t('refreshFailed') })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <>
      <button
        type="button"
        className="refresh-btn"
        onClick={() => setIsConfirmOpen(true)}
        disabled={isSubmitting}
      >
        <RefreshIcon />
        {t('refreshButton')}
      </button>

      {isConfirmOpen && (
        <div className="modal-overlay" role="presentation" onClick={() => setIsConfirmOpen(false)}>
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="refresh-confirm-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="refresh-confirm-title" className="modal-title">
              {t('refreshConfirmTitle')}
            </h2>
            <p className="modal-body">{t('refreshConfirmBody')}</p>
            <div className="modal-actions">
              <button type="button" className="modal-btn modal-btn-secondary" onClick={() => setIsConfirmOpen(false)}>
                {t('refreshConfirmCancel')}
              </button>
              <button type="button" className="modal-btn modal-btn-primary" onClick={handleConfirm}>
                {t('refreshConfirmYes')}
              </button>
            </div>
          </div>
        </div>
      )}

      {statusMessage && (
        <div className={`refresh-status refresh-status-${statusMessage.kind}`} role="status">
          <span>{statusMessage.text}</span>
          <button
            type="button"
            className="refresh-status-close"
            aria-label={t('closeLabel')}
            onClick={() => setStatusMessage(null)}
          >
            ×
          </button>
        </div>
      )}
    </>
  )
}
