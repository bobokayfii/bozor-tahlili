import { describe, it, expect } from 'vitest'
import { getProductColumns } from './productColumns'
import type { Product } from './types'

const baseProduct: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'Test mahsulot',
  rate_min: 20,
  rate_max: 25,
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

describe('getProductColumns', () => {
  it('returns the down-payment column set in pptx order for credit_down_payment', () => {
    const columns = getProductColumns('credit_down_payment')
    expect(columns.map((c) => c.label)).toEqual([
      "Boshlang'ich badal",
      'Imtiyozli davr',
      'Kredit miqdori',
      "To'lov usuli",
    ])
  })

  it('returns the special-terms column set in pptx order for credit_special_terms', () => {
    const columns = getProductColumns('credit_special_terms')
    expect(columns.map((c) => c.label)).toEqual([
      'Kredit miqdori',
      'Imtiyozli davr',
      'Maxsus shartlari',
      "To'lov usuli",
    ])
  })

  it('defaults to the down-payment column set for an unknown or missing schema', () => {
    expect(getProductColumns(undefined).map((c) => c.label)).toContain("Boshlang'ich badal")
    expect(getProductColumns('something_else').map((c) => c.label)).toContain("Boshlang'ich badal")
  })

  it('renders down payment percentage or a dash when absent', () => {
    const [downPayment] = getProductColumns('credit_down_payment')
    expect(downPayment.render(baseProduct)).toBe('30%')
    expect(downPayment.render({ ...baseProduct, down_payment_pct: null })).toBe('—')
  })

  it('renders grace period as Bor/Yo\'q, or a dash when unknown', () => {
    const [, gracePeriod] = getProductColumns('credit_down_payment')
    expect(gracePeriod.render(baseProduct)).toBe('Bor')
    expect(gracePeriod.render({ ...baseProduct, grace_period_months: 0 })).toBe("Yo'q")
    expect(gracePeriod.render({ ...baseProduct, grace_period_months: null })).toBe('—')
  })

  it('formats the credit amount in millions of soum', () => {
    const [, , amount] = getProductColumns('credit_down_payment')
    expect(amount.render(baseProduct)).toBe("800 mln so'm")
    expect(amount.render({ ...baseProduct, amount_max_som: 41_000_000 })).toBe("41 mln so'm")
    expect(amount.render({ ...baseProduct, amount_max_som: 1_012_500_000 })).toBe("1012.5 mln so'm")
  })

  it('renders special terms text or a dash when absent', () => {
    // credit_special_terms order is [amount, gracePeriod, specialTerms, paymentMethod]
    const [, , specialTerms] = getProductColumns('credit_special_terms')
    expect(specialTerms.render({ ...baseProduct, special_terms: 'Kredit yuklamasi hisobga olinadi' })).toBe(
      'Kredit yuklamasi hisobga olinadi',
    )
    expect(specialTerms.render({ ...baseProduct, special_terms: null })).toBe('—')
  })

  it('renders payment method or a dash when absent', () => {
    const [, , , paymentMethod] = getProductColumns('credit_down_payment')
    expect(paymentMethod.render(baseProduct)).toBe('Annuitet')
    expect(paymentMethod.render({ ...baseProduct, payment_method: null })).toBe('—')
  })

  it('omits Imtiyozli davr and Maxsus shartlari for the mikroqarz category, regardless of schema', () => {
    const mikroqarzColumns = getProductColumns('credit_special_terms', 'mikroqarz')
    expect(mikroqarzColumns.map((c) => c.label)).toEqual(['Kredit miqdori', "To'lov usuli"])

    const mikroqarzOnlaynColumns = getProductColumns('credit_special_terms', 'mikroqarz_onlayn')
    expect(mikroqarzOnlaynColumns.map((c) => c.label)).toEqual(['Kredit miqdori', "To'lov usuli"])
  })

  it('falls back to "Annuitet, Differensial" for mikroqarz payment method when unstated', () => {
    const [, paymentMethod] = getProductColumns('credit_special_terms', 'mikroqarz')
    expect(paymentMethod.render(baseProduct)).toBe('Annuitet')
    expect(paymentMethod.render({ ...baseProduct, payment_method: null })).toBe('Annuitet, Differensial')
  })
})
