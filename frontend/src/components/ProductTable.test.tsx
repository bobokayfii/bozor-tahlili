import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProductTable } from './ProductTable'
import type { Product, UnavailableBank } from '../lib/types'

const sampleProduct: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  down_payment_pct: 30,
  grace_period_months: 3,
  payment_method: 'Annuitet',
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

const cheaperProduct: Product = {
  ...sampleProduct,
  bank: 'NBU',
  product_name: 'NBU Avtokredit',
  rate_min: 20.9,
  rate_max: 23.9,
}

describe('ProductTable', () => {
  it('shows a loading skeleton instead of the empty-state message while loading', () => {
    render(<ProductTable products={[]} isLoading />)
    expect(screen.getByLabelText('Yuklanmoqda')).toBeInTheDocument()
    expect(
      screen.queryByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).not.toBeInTheDocument()
  })

  it('shows the empty-state message when there are no products', () => {
    render(<ProductTable products={[]} />)
    expect(
      screen.getByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).toBeInTheDocument()
  })

  it('renders one row per product with bank and rate range', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('24.9% – 27.9%')).toBeInTheDocument()
  })

  it('renders a single rate value (not "X%-X%") when rate_min equals rate_max', () => {
    const flatRateProduct: Product = { ...sampleProduct, rate_min: 0, rate_max: 0 }
    render(<ProductTable products={[flatRateProduct]} />)
    expect(screen.getByText('0%')).toBeInTheDocument()
    expect(screen.queryByText('0% – 0%')).not.toBeInTheDocument()
  })

  it('ranks products by cheapest rate first and flags the SQB row', () => {
    render(<ProductTable products={[sampleProduct, cheaperProduct]} />)
    const rows = screen.getAllByText(/^0[12]$/)
    expect(rows[0]).toHaveTextContent('01')
    expect(screen.getByText('NBU').closest('.rate-row')).toHaveClass('is-best')
    expect(screen.getByText('Biz')).toBeInTheDocument()
    expect(screen.getByText('SQB').closest('.rate-row')).toHaveClass('is-house')
  })

  it('defaults to the credit_down_payment column set when no schema prop is given', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText("Boshlang'ich badal")).toBeInTheDocument()
    expect(screen.getByText('30%')).toBeInTheDocument()
    expect(screen.getByText('Annuitet')).toBeInTheDocument()
    expect(screen.getByText('Bor')).toBeInTheDocument()
    expect(screen.getByText('Kredit miqdori')).toBeInTheDocument()
    expect(screen.getByText("800 mln so'm")).toBeInTheDocument()
  })

  it('falls back to a dash for missing optional fields', () => {
    const productWithoutExtras: Product = {
      ...sampleProduct,
      requires_collateral: false,
      down_payment_pct: null,
      payment_method: null,
      grace_period_months: null,
    }
    render(<ProductTable products={[productWithoutExtras]} />)
    expect(screen.getAllByText('—')).toHaveLength(3)
  })

  it('renders the credit_special_terms column set: Maxsus shartlari shown, Boshlang\'ich badal hidden', () => {
    const microloanProduct: Product = {
      ...sampleProduct,
      category: 'mikroqarz',
      down_payment_pct: null,
      special_terms: 'Kredit yuklamasi hisobga olinadi',
    }
    render(<ProductTable products={[microloanProduct]} schema="credit_special_terms" />)
    expect(screen.getByText('Maxsus shartlari')).toBeInTheDocument()
    expect(screen.getByText('Kredit yuklamasi hisobga olinadi')).toBeInTheDocument()
    expect(screen.queryByText("Boshlang'ich badal")).not.toBeInTheDocument()
  })

  it('renders the credit_down_payment column set: Boshlang\'ich badal shown, Maxsus shartlari hidden', () => {
    render(<ProductTable products={[sampleProduct]} schema="credit_down_payment" />)
    expect(screen.getByText("Boshlang'ich badal")).toBeInTheDocument()
    expect(screen.queryByText('Maxsus shartlari')).not.toBeInTheDocument()
  })

  it('hides Imtiyozli davr and Maxsus shartlari for the mikroqarz category and defaults unstated payment method to both methods', () => {
    const microloanProduct: Product = {
      ...sampleProduct,
      category: 'mikroqarz',
      payment_method: null,
    }
    render(<ProductTable products={[microloanProduct]} schema="credit_special_terms" category="mikroqarz" />)
    expect(screen.queryByText('Imtiyozli davr')).not.toBeInTheDocument()
    expect(screen.queryByText('Maxsus shartlari')).not.toBeInTheDocument()
    expect(screen.getByText('Annuitet, Differensial')).toBeInTheDocument()
  })

  it('shows the empty-state message when there are no products and no unavailable banks', () => {
    render(<ProductTable products={[]} unavailableBanks={[]} />)
    expect(
      screen.getByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).toBeInTheDocument()
  })

  it('renders unavailable banks as a separate row without affecting ranking', () => {
    const unavailableBanks: UnavailableBank[] = [{ bank: 'TBC Bank', reason: 'Mahsulot mavjud emas' }]
    render(<ProductTable products={[sampleProduct, cheaperProduct]} unavailableBanks={unavailableBanks} />)

    expect(screen.getByText('TBC Bank')).toBeInTheDocument()
    expect(screen.getByText('Mahsulot mavjud emas')).toBeInTheDocument()
    // Ranking (rank "01", best-rate highlight) is unaffected by the unavailable entry.
    expect(screen.getByText('NBU').closest('.rate-row')).toHaveClass('is-best')
    expect(screen.getByText('TBC Bank').closest('.rate-row')).toHaveClass('rate-row-unavailable')
  })

  it('shows unavailable banks even when there are zero products for the category', () => {
    const unavailableBanks: UnavailableBank[] = [{ bank: 'TBC Bank', reason: 'Mahsulot mavjud emas' }]
    render(<ProductTable products={[]} unavailableBanks={unavailableBanks} />)

    expect(screen.getByText('TBC Bank')).toBeInTheDocument()
    expect(
      screen.queryByText("Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda."),
    ).not.toBeInTheDocument()
  })
})
