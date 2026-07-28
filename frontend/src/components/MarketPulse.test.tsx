import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactElement } from 'react'
import { MarketPulse } from './MarketPulse'
import { fetchProductExplanation } from '../lib/api'
import { LanguageProvider } from '../lib/LanguageContext'
import type { Product } from '../lib/types'

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

vi.mock('../lib/api', () => ({
  fetchProductExplanation: vi.fn(),
}))

const products: Product[] = [
  {
    bank: 'SQB',
    category: 'mikroqarz',
    product_name: 'SQB Mikroqarz',
    rate_min: 24.9,
    rate_max: 27.9,
    term_min_months: 12,
    term_max_months: 60,
    amount_max_som: 100_000_000,
    requires_collateral: true,
    down_payment_pct: null,
    grace_period_months: null,
    payment_method: 'Annuitet',
    special_terms: null,
    scraped_at: '2026-07-08T10:00:00Z',
  },
  {
    bank: 'NBU',
    category: 'mikroqarz',
    product_name: 'NBU Mikroqarz',
    rate_min: 20.9,
    rate_max: 23.9,
    term_min_months: 6,
    term_max_months: 48,
    amount_max_som: 150_000_000,
    requires_collateral: false,
    down_payment_pct: null,
    grace_period_months: null,
    payment_method: null,
    special_terms: null,
    scraped_at: '2026-07-08T10:00:00Z',
  },
]

const mockedFetchProductExplanation = vi.mocked(fetchProductExplanation)

describe('MarketPulse featured card + AI note', () => {
  beforeEach(() => {
    mockedFetchProductExplanation.mockReset()
  })

  it('features the same product the table would rank first (lowest rate_min)', () => {
    mockedFetchProductExplanation.mockResolvedValue({ explanation: 'NBU past stavka bilan ajralib turadi.' })

    renderWithLanguage(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    // NBU has the lowest rate_min (20.9 vs SQB's 24.9), so it must be featured —
    // matching ProductTable's own `sort((a, b) => a.rate_min - b.rate_min)`.
    expect(screen.getByText('NBU')).toBeInTheDocument()
    expect(screen.getByText('NBU Mikroqarz')).toBeInTheDocument()
    expect(screen.queryByText('SQB Mikroqarz')).not.toBeInTheDocument()
  })

  it("requests the AI note for exactly the featured product's own fields, not a separately-ranked pick", async () => {
    mockedFetchProductExplanation.mockResolvedValue({ explanation: 'NBU past stavka bilan ajralib turadi.' })

    renderWithLanguage(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    await screen.findByText('NBU past stavka bilan ajralib turadi.')

    expect(mockedFetchProductExplanation).toHaveBeenCalledWith({
      category: 'mikroqarz',
      bank: 'NBU',
      product_name: 'NBU Mikroqarz',
      rate_min: 20.9,
      rate_max: 23.9,
      term_min_months: 6,
      term_max_months: 48,
      amount_max_som: 150_000_000,
      requires_collateral: false,
      down_payment_pct: null,
      language: 'uz',
    })
  })

  it('shows an error message instead of the stale "tez orada" placeholder when the request fails', async () => {
    mockedFetchProductExplanation.mockRejectedValue(new Error("AI izohini olib bo'lmadi: 500"))

    renderWithLanguage(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    expect(await screen.findByText("AI izohini olib bo'lmadi: 500")).toBeInTheDocument()
    expect(screen.queryByText(/tez orada/i)).not.toBeInTheDocument()
  })

  it('translates static labels and sends language: "ru" to the explain-product request when lang is ru', async () => {
    window.localStorage.setItem('bozor-tahlili-lang', 'ru')
    mockedFetchProductExplanation.mockResolvedValue({ explanation: 'NBU выделяется низкой ставкой.' })

    renderWithLanguage(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    await screen.findByText('NBU выделяется низкой ставкой.')

    expect(screen.getByText('Пульс рынка · Лучшее предложение')).toBeInTheDocument()
    expect(screen.getByText('Ставка')).toBeInTheDocument()
    expect(screen.getByText('Залог')).toBeInTheDocument()
    expect(mockedFetchProductExplanation).toHaveBeenCalledWith(expect.objectContaining({ language: 'ru' }))
    window.localStorage.removeItem('bozor-tahlili-lang')
  })
})
