import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'

interface ProductTableProps {
  products: Product[]
  isLoading?: boolean
  schema?: string
}

function SkeletonRows({ schema }: { schema?: string }) {
  const columns = getProductColumns(schema)

  return (
    <div className="rate-board" aria-busy="true" aria-label="Yuklanmoqda">
      <div className="rate-board-head">
        <span>#</span>
        <span>Bank</span>
        <span>Mahsulot</span>
        <span>Stavka</span>
        <span>Muddat</span>
        {columns.map((column) => (
          <span key={column.key}>{column.label}</span>
        ))}
      </div>
      {[0, 1, 2].map((row) => (
        <div className="rate-row rate-row-skeleton" key={row}>
          <span className="skeleton skeleton-rank" />
          <span className="skeleton skeleton-bank" />
          <span className="skeleton skeleton-product" />
          <span className="skeleton skeleton-figure" />
          <span className="skeleton skeleton-term" />
          {columns.map((column) => (
            <span className="skeleton skeleton-term" key={column.key} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function ProductTable({ products, isLoading = false, schema }: ProductTableProps) {
  const columns = getProductColumns(schema)

  if (isLoading) {
    return <SkeletonRows schema={schema} />
  }

  if (products.length === 0) {
    return (
      <p className="empty-state">
        Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda.
      </p>
    )
  }

  const ranked = [...products].sort((a, b) => a.rate_min - b.rate_min)
  const bestRate = ranked[0].rate_min
  const lastIndex = ranked.length - 1

  return (
    <div className="rate-board">
      <div className="rate-board-head">
        <span>#</span>
        <span>Bank</span>
        <span>Mahsulot</span>
        <span>Stavka</span>
        <span>Muddat</span>
        {columns.map((column) => (
          <span key={column.key}>{column.label}</span>
        ))}
      </div>
      {ranked.map((product, index) => {
        const isBest = product.rate_min === bestRate
        const house = isHouseBank(product.bank)
        const fillPct = lastIndex === 0 ? 100 : 100 - (index / lastIndex) * 100

        const rowClass = ['rate-row', isBest && 'is-best', house && 'is-house']
          .filter(Boolean)
          .join(' ')

        return (
          <div className={rowClass} key={`${product.bank}-${product.product_name}-${index}`}>
            <span className="rate-rank">{String(index + 1).padStart(2, '0')}</span>
            <span className="rate-bank">
              {getBankLogo(product.bank) && (
                <img src={getBankLogo(product.bank)} alt="" className="rate-bank-logo" />
              )}
              <span className="rate-bank-name">{product.bank}</span>
              {house && <span className="house-flag">Biz</span>}
            </span>
            <span className="rate-product">{product.product_name}</span>
            <span className="rate-figure">
              <span className="rate-figure-value">
                {product.rate_min}% – {product.rate_max}%
              </span>
              <span className="rate-bar-track">
                <span className="rate-bar-fill" style={{ width: `${fillPct}%` }} />
              </span>
            </span>
            <span className="rate-term">
              {product.term_min_months}–{product.term_max_months} oy
            </span>
            {columns.map((column) => {
              const value = column.render(product)
              return (
                <span className="rate-extra" key={column.key} title={value}>
                  {value}
                </span>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}
