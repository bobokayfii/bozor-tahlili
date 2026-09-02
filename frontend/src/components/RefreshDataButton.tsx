import { useCallback, useState } from 'react'
import { triggerScrapeRefresh } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { useModalFocusTrap } from '../lib/useModalFocusTrap'
import { RefreshIcon } from './icons'

type StatusMessage = { kind: 'success' | 'warning' | 'error'; text: string } | null

export function RefreshDataButton() {
  const { t } = useLanguage()
  const [isConfirmOpen, setIsConfirmOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [statusMessage, setStatusMessage] = useState<StatusMessage>(null)
  // Stable reference: this component stays mounted while the dialog itself
  // is conditionally rendered, so an unstable callback would re-run the
  // trap's setup/teardown (and re-steal focus) on every unrelated re-render
  // while the dialog is open, not just on open/close transitions.
  const closeConfirm = useCallback(() => setIsConfirmOpen(false), [])
  const dialogRef = useModalFocusTrap(isConfirmOpen, closeConfirm)

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
        <div className="modal-overlay" role="presentation" onClick={closeConfirm}>
          {/* onClick only stops the overlay's close-on-click from firing for
              clicks inside the dialog - it's event-bubbling containment, not
              a user-facing affordance, so it needs no keyboard equivalent. */}
          {/* eslint-disable-next-line jsx-a11y/click-events-have-key-events, jsx-a11y/no-noninteractive-element-interactions */}
          <div
            className="modal-card"
            role="dialog"
            aria-modal="true"
            aria-labelledby="refresh-confirm-title"
            ref={dialogRef}
            tabIndex={-1}
            onClick={(event) => event.stopPropagation()}
          >
            <h2 id="refresh-confirm-title" className="modal-title">
              {t('refreshConfirmTitle')}
            </h2>
            <p className="modal-body">{t('refreshConfirmBody')}</p>
            <div className="modal-actions">
              <button type="button" className="modal-btn modal-btn-secondary" onClick={closeConfirm}>
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
