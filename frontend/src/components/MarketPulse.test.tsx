import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MarketPulse } from './MarketPulse'
import { fetchRecommendation } from '../lib/api'
import type { Product } from '../lib/types'

vi.mock('../lib/api', () => ({
  fetchRecommendation: vi.fn(),
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

const mockedFetchRecommendation = vi.mocked(fetchRecommendation)

describe('MarketPulse AI recommendation', () => {
  beforeEach(() => {
    mockedFetchRecommendation.mockReset()
  })

  it('requests a recommendation derived from the currently loaded products, not a hardcoded default', async () => {
    mockedFetchRecommendation.mockResolvedValue({ recommendations: [], explanation: 'SQB eng yaxshi tanlov.' })

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    await screen.findByText('SQB eng yaxshi tanlov.')

    expect(mockedFetchRecommendation).toHaveBeenCalledWith({
      category: 'mikroqarz',
      // term_min_months bo'yicha eng kattasi (12), amount_max_som bo'yicha eng kichigi (100 mln) —
      // shu bilan ikkala mahsulot ham mos keladigan mezon hosil bo'ladi.
      term_months: 12,
      amount_som: 100_000_000,
      collateral_ok: true,
    })
  })

  it('shows the AI explanation text once the request resolves', async () => {
    mockedFetchRecommendation.mockResolvedValue({
      recommendations: [{ bank: 'SQB', product_name: 'SQB Mikroqarz', score: 0.9 }],
      explanation: 'SQB tavsiya etiladi, chunki eng past stavkaga ega.',
    })

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    expect(await screen.findByText('SQB tavsiya etiladi, chunki eng past stavkaga ega.')).toBeInTheDocument()
  })

  it('shows an error message instead of the stale "tez orada" placeholder when the request fails', async () => {
    mockedFetchRecommendation.mockRejectedValue(new Error("AI tavsiyasini olib bo'lmadi: 500"))

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    expect(await screen.findByText("AI tavsiyasini olib bo'lmadi: 500")).toBeInTheDocument()
    expect(screen.queryByText(/tez orada/i)).not.toBeInTheDocument()
  })
})
