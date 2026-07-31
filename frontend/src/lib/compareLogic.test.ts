import { describe, it, expect } from 'vitest'
import type { Product } from './types'
import { getCompareKey, bestIndexesByNumber, bestIndexesByGracePeriod } from './compareLogic'

const base: Product = {
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

describe('getCompareKey', () => {
  it('combines bank and product name with a double-colon separator', () => {
    expect(getCompareKey(base)).toBe('SQB::SQB Avtokredit')
  })

  it('produces different keys for the same bank with two different products', () => {
    const other: Product = { ...base, product_name: 'SQB Avtokredit Plus' }
    expect(getCompareKey(base)).not.toBe(getCompareKey(other))
  })
})

describe('bestIndexesByNumber', () => {
  it('marks the single lowest value as best when direction is lower', () => {
    expect(bestIndexesByNumber([24.9, 20.9, 27.9], 'lower')).toEqual(new Set([1]))
  })

  it('marks the single highest value as best when direction is higher', () => {
    expect(bestIndexesByNumber([800, 900, 500], 'higher')).toEqual(new Set([1]))
  })

  it('marks all tied values as best', () => {
    expect(bestIndexesByNumber([20, 20, 30], 'lower')).toEqual(new Set([0, 1]))
  })

  it('ignores null values when picking the best', () => {
    expect(bestIndexesByNumber([null, 20, 30], 'lower')).toEqual(new Set([1]))
  })

  it('returns an empty set when every value is null', () => {
    expect(bestIndexesByNumber([null, null], 'lower')).toEqual(new Set())
  })
})

describe('bestIndexesByGracePeriod', () => {
  it('marks entries with a positive grace period as best', () => {
    expect(bestIndexesByGracePeriod([3, 0, null])).toEqual(new Set([0]))
  })

  it('marks all entries with a positive grace period when more than one qualifies', () => {
    expect(bestIndexesByGracePeriod([3, 6, 0])).toEqual(new Set([0, 1]))
  })

  it('returns an empty set when nobody has a grace period', () => {
    expect(bestIndexesByGracePeriod([0, null, 0])).toEqual(new Set())
  })
})
