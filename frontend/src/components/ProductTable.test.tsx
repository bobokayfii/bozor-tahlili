import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { ProductTable } from './ProductTable'
import type { Product } from '../lib/types'

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
  grace_period_months: null,
  payment_method: null,
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

describe('ProductTable', () => {
  it('shows the empty-state message when there are no products', () => {
    render(<ProductTable products={[]} />)
    expect(screen.getByText("Bu kategoriya uchun hozircha ma'lumot yo'q.")).toBeInTheDocument()
  })

  it('renders one row per product with bank and rate range', () => {
    render(<ProductTable products={[sampleProduct]} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('24.9% – 27.9%')).toBeInTheDocument()
  })
})
