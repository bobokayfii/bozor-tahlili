import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MarketPulse } from './MarketPulse'
import { fetchProductExplanation } from '../lib/api'
import type { Product } from '../lib/types'

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

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    // NBU has the lowest rate_min (20.9 vs SQB's 24.9), so it must be featured —
    // matching ProductTable's own `sort((a, b) => a.rate_min - b.rate_min)`.
    expect(screen.getByText('NBU')).toBeInTheDocument()
    expect(screen.getByText('NBU Mikroqarz')).toBeInTheDocument()
    expect(screen.queryByText('SQB Mikroqarz')).not.toBeInTheDocument()
  })

  it("requests the AI note for exactly the featured product's own fields, not a separately-ranked pick", async () => {
    mockedFetchProductExplanation.mockResolvedValue({ explanation: 'NBU past stavka bilan ajralib turadi.' })

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

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
    })
  })

  it('shows an error message instead of the stale "tez orada" placeholder when the request fails', async () => {
    mockedFetchProductExplanation.mockRejectedValue(new Error("AI izohini olib bo'lmadi: 500"))

    render(<MarketPulse category="mikroqarz" products={products} updatedLabel={null} />)

    expect(await screen.findByText("AI izohini olib bo'lmadi: 500")).toBeInTheDocument()
    expect(screen.queryByText(/tez orada/i)).not.toBeInTheDocument()
  })
})
