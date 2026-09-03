import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { ScrapeStatusPanel } from './ScrapeStatusPanel'
import { LanguageProvider } from '../lib/LanguageContext'
import { fetchScrapeRuns } from '../lib/api'

vi.mock('../lib/api', () => ({
  fetchScrapeRuns: vi.fn(),
}))

const mockedFetchScrapeRuns = vi.mocked(fetchScrapeRuns)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('ScrapeStatusPanel', () => {
  it('shows a failed bank with its error message', async () => {
    mockedFetchScrapeRuns.mockResolvedValue([
      {
        bank: 'OFB', status: 'failed', started_at: '2026-09-02T10:00:00Z',
        finished_at: '2026-09-02T10:01:00Z', error_message: '90s ichida javob bermadi (timeout)',
        products_found: 0,
      },
    ])
    renderWithLanguage(<ScrapeStatusPanel />)

    expect(await screen.findByText('OFB')).toBeInTheDocument()
    expect(screen.getByText('Xato')).toBeInTheDocument()
    expect(screen.getByText('90s ichida javob bermadi (timeout)')).toBeInTheDocument()
  })

  it('shows a successful bank with its product count and no error line', async () => {
    mockedFetchScrapeRuns.mockResolvedValue([
      {
        bank: 'SQB', status: 'success', started_at: '2026-09-02T10:00:00Z',
        finished_at: '2026-09-02T10:01:00Z', error_message: null, products_found: 12,
      },
    ])
    renderWithLanguage(<ScrapeStatusPanel />)

    expect(await screen.findByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('Muvaffaqiyatli')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
  })

  it('shows a bank that has never run without a timestamp', async () => {
    mockedFetchScrapeRuns.mockResolvedValue([
      { bank: 'NewBank', status: 'never_run', started_at: null, finished_at: null, error_message: null, products_found: 0 },
    ])
    renderWithLanguage(<ScrapeStatusPanel />)

    expect(await screen.findByText('NewBank')).toBeInTheDocument()
    expect(screen.getByText('Hech qachon ishlamagan')).toBeInTheDocument()
  })

  it('shows an error message instead of failing silently when the fetch itself fails', async () => {
    mockedFetchScrapeRuns.mockRejectedValue(new Error("Ulanib bo'lmadi"))
    renderWithLanguage(<ScrapeStatusPanel />)

    expect(await screen.findByText("Ulanib bo'lmadi")).toBeInTheDocument()
  })
})
