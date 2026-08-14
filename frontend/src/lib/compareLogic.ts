import type { Product } from './types'

export function getCompareKey(product: Product): string {
  return `${product.bank}::${product.product_name}`
}

export function bestIndexesByNumber(values: (number | null)[], direction: 'lower' | 'higher'): Set<number> {
  const defined = values
    .map((value, index) => ({ value, index }))
    .filter((entry): entry is { value: number; index: number } => entry.value !== null)

  if (defined.length === 0) return new Set()

  const best =
    direction === 'lower'
      ? Math.min(...defined.map((entry) => entry.value))
      : Math.max(...defined.map((entry) => entry.value))

  return new Set(defined.filter((entry) => entry.value === best).map((entry) => entry.index))
}

export function bestIndexesByGracePeriod(values: (number | null)[]): Set<number> {
  return new Set(
    values.reduce<number[]>((acc, value, index) => {
      if (value !== null && value > 0) acc.push(index)
      return acc
    }, []),
  )
}
