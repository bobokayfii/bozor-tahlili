import type { Product } from '../lib/types'
import { getBankLogo } from '../lib/bankLogos'
import { getCompareKey } from '../lib/compareLogic'
import { useLanguage } from '../lib/LanguageContext'

interface CompareBarProps {
  products: Product[]
  onRemove: (key: string) => void
  onOpen: () => void
  onClear: () => void
}

export function CompareBar({ products, onRemove, onOpen, onClear }: CompareBarProps) {
  const { t } = useLanguage()

  if (products.length === 0) return null

  return (
    <div className="compare-bar" role="region" aria-live="polite" aria-label={t('compareBarLabel')}>
      <ul className="compare-bar-chips">
        {products.map((product) => {
          const key = getCompareKey(product)
          const logo = getBankLogo(product.bank)
          return (
            <li className="compare-chip" key={key}>
              {logo && <img src={logo} alt="" className="compare-chip-logo" />}
              <span className="compare-chip-name">{product.bank}</span>
              <button
                type="button"
                className="compare-chip-remove"
                aria-label={t('closeLabel')}
                onClick={() => onRemove(key)}
              >
                ×
              </button>
            </li>
          )
        })}
      </ul>
      <div className="compare-bar-actions">
        <button type="button" className="compare-bar-clear" onClick={onClear}>
          {t('compareBarClear')}
        </button>
        <button
          type="button"
          className="modal-btn modal-btn-primary compare-bar-open"
          onClick={onOpen}
          disabled={products.length < 2}
        >
          {t('compareButton')} ({products.length})
        </button>
      </div>
    </div>
  )
}
