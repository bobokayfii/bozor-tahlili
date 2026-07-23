import type { Product, UnavailableBank } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'

interface ProductTableProps {
  products: Product[]
  isLoading?: boolean
  schema?: string
  category?: string
  unavailableBanks?: UnavailableBank[]
}

// Reyting/muddat kabi sobit ustunlar har doim bir xil nisbatda qoladi;
// "qo'shimcha" ustunlar soni kategoriyaga qarab farq qiladi (masalan,
// mikroqarz endi faqat 2 ta, boshqalari 4 ta) — shu sabab ularning kengligi
// sobit CSS shablon o'rniga ustunlar soniga qarab dinamik hisoblanadi, aks
// holda kamroq ustunli kategoriyalarda jadval o'ng tomondan bo'sh qisilib
// qoladi. Har bir fr ustun minmax(0, ...) bilan o'ralgan — aks holda grid
// ustuni matn kontentining eng kichik "shrink qilib bo'lmaydigan" kengligiga
// (min-content) qarab kattalashadi va tor ekranlarda butun jadval, hatto
// butun sahifa, gorizontal tashqariga chiqib ketadi (mobil overflow xatosi).
function gridTemplateColumns(extraColumnCount: number): string {
  const extraTracks = Array(extraColumnCount).fill('minmax(0, 1fr)').join(' ')
  return `32px minmax(0, 1.1fr) minmax(0, 1.3fr) minmax(0, 0.85fr) minmax(0, 0.6fr) ${extraTracks}`.trim()
}

function SkeletonRows({ schema, category }: { schema?: string; category?: string }) {
  const columns = getProductColumns(schema, category)
  const gridStyle = { gridTemplateColumns: gridTemplateColumns(columns.length) }

  return (
    <div className="rate-board" aria-busy="true" aria-label="Yuklanmoqda">
      <div className="rate-board-head" style={gridStyle}>
        <span>#</span>
        <span>Bank</span>
        <span className="rate-head-product">Mahsulot</span>
        <span>Stavka</span>
        <span className="rate-head-term">Muddat</span>
        {columns.map((column) => (
          <span className="rate-head-extra" key={column.key}>
            {column.label}
          </span>
        ))}
      </div>
      {[0, 1, 2].map((row) => (
        <div className="rate-row rate-row-skeleton" key={row} style={gridStyle}>
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

export function ProductTable({
  products,
  isLoading = false,
  schema,
  category,
  unavailableBanks = [],
}: ProductTableProps) {
  const columns = getProductColumns(schema, category)
  const gridStyle = { gridTemplateColumns: gridTemplateColumns(columns.length) }

  if (isLoading) {
    return <SkeletonRows schema={schema} category={category} />
  }

  if (products.length === 0 && unavailableBanks.length === 0) {
    return (
      <p className="empty-state">
        Bu toifa uchun hozircha ma'lumot yo'q — banklar sahifalari navbatda kuzatilmoqda.
      </p>
    )
  }

  const ranked = [...products].sort((a, b) => a.rate_min - b.rate_min)
  const bestRate = ranked.length > 0 ? ranked[0].rate_min : null
  const lastIndex = ranked.length - 1

  return (
    <div className="rate-board">
      <div className="rate-board-head" style={gridStyle}>
        <span>#</span>
        <span>Bank</span>
        <span className="rate-head-product">Mahsulot</span>
        <span>Stavka</span>
        <span className="rate-head-term">Muddat</span>
        {columns.map((column) => (
          <span className="rate-head-extra" key={column.key}>
            {column.label}
          </span>
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
          <div className={rowClass} key={`${product.bank}-${product.product_name}-${index}`} style={gridStyle}>
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
                {product.rate_min === product.rate_max
                  ? `${product.rate_min}%`
                  : `${product.rate_min}% – ${product.rate_max}%`}
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
      {unavailableBanks.map((item) => (
        <div className="rate-row rate-row-unavailable" key={item.bank} style={gridStyle}>
          <span className="rate-rank" aria-hidden="true">
            —
          </span>
          <span className="rate-bank">
            {getBankLogo(item.bank) && <img src={getBankLogo(item.bank)} alt="" className="rate-bank-logo" />}
            <span className="rate-bank-name">{item.bank}</span>
          </span>
          <span className="rate-unavailable-reason" style={{ gridColumn: '3 / -1' }}>
            {item.reason}
          </span>
        </div>
      ))}
    </div>
  )
}
