import { useEffect, useRef } from 'react'
import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { getProductColumns } from '../lib/productColumns'
import { getCompareKey, bestIndexesByNumber, bestIndexesByGracePeriod } from '../lib/compareLogic'
import { useLanguage } from '../lib/LanguageContext'
import { translate, type Lang } from '../lib/i18n'

interface CompareModalProps {
  products: Product[]
  schema?: string
  category?: string
  onClose: () => void
  onRemove: (key: string) => void
}

function formatRateRange(product: Product): string {
  return product.rate_min === product.rate_max
    ? `${product.rate_min}%`
    : `${product.rate_min}% – ${product.rate_max}%`
}

function formatTermRange(product: Product, lang: Lang): string {
  const unit = translate(lang, 'monthUnit')
  return product.term_min_months === product.term_max_months
    ? `${product.term_min_months} ${unit}`
    : `${product.term_min_months}–${product.term_max_months} ${unit}`
}

const NUMERIC_EXTRACTORS: Record<string, (product: Product) => number | null> = {
  down_payment: (product) => product.down_payment_pct,
  amount: (product) => product.amount_max_som,
}

const NUMERIC_DIRECTIONS: Record<string, 'lower' | 'higher'> = {
  down_payment: 'lower',
  amount: 'higher',
}

function cellClass(isBest: boolean): string {
  return isBest ? 'compare-cell compare-cell-best' : 'compare-cell'
}

export function CompareModal({ products, schema, category, onClose, onRemove }: CompareModalProps) {
  const { lang, t } = useLanguage()
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    cardRef.current?.focus()
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const columns = getProductColumns(schema, category, lang)
  const gridStyle = { gridTemplateColumns: `160px repeat(${products.length}, minmax(0, 1fr))` }
  const rateBestIndexes = bestIndexesByNumber(
    products.map((product) => product.rate_min),
    'lower',
  )

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card compare-modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="compare-modal-title"
        tabIndex={-1}
        ref={cardRef}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="compare-modal-head">
          <h2 id="compare-modal-title" className="modal-title">
            {t('compareModalTitle')}
          </h2>
          <button type="button" className="compare-modal-close" aria-label={t('closeLabel')} onClick={onClose}>
            ×
          </button>
        </div>

        <div className="compare-table-wrap">
          <div className="compare-row compare-row-head" style={gridStyle}>
            <span className="compare-attr-label" />
            {products.map((product) => {
              const key = getCompareKey(product)
              const logo = getBankLogo(product.bank)
              const house = isHouseBank(product.bank)
              return (
                <div className="compare-col-head" key={key}>
                  <button
                    type="button"
                    className="compare-col-remove"
                    aria-label={t('closeLabel')}
                    onClick={() => onRemove(key)}
                  >
                    ×
                  </button>
                  {logo && <img src={logo} alt="" className="compare-col-logo" />}
                  <span className="compare-col-bank">
                    {product.bank}
                    {house && <span className="house-flag">{t('houseFlag')}</span>}
                  </span>
                  <span className="compare-col-product">{product.product_name}</span>
                </div>
              )
            })}
          </div>

          <div className="compare-row" style={gridStyle}>
            <span className="compare-attr-label">{t('tableRate')}</span>
            {products.map((product, index) => (
              <span className={cellClass(rateBestIndexes.has(index))} key={getCompareKey(product)}>
                {formatRateRange(product)}
              </span>
            ))}
          </div>

          <div className="compare-row" style={gridStyle}>
            <span className="compare-attr-label">{t('tableTerm')}</span>
            {products.map((product) => (
              <span className="compare-cell" key={getCompareKey(product)}>
                {formatTermRange(product, lang)}
              </span>
            ))}
          </div>

          {columns.map((column) => {
            const isNumeric = column.key in NUMERIC_EXTRACTORS
            const bestIndexes = isNumeric
              ? bestIndexesByNumber(products.map(NUMERIC_EXTRACTORS[column.key]), NUMERIC_DIRECTIONS[column.key])
              : column.key === 'grace_period'
                ? bestIndexesByGracePeriod(products.map((product) => product.grace_period_months))
                : new Set<number>()

            return (
              <div className="compare-row" style={gridStyle} key={column.key}>
                <span className="compare-attr-label">{column.label}</span>
                {products.map((product, index) => (
                  <span className={cellClass(bestIndexes.has(index))} key={getCompareKey(product)}>
                    {column.render(product)}
                  </span>
                ))}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
