import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { MarketPulse } from './MarketPulse'
import { ProductTable } from './ProductTable'
import { ClockIcon } from './icons'
import { fetchProducts, fetchUnavailableBanks } from '../lib/api'
import { getCategoryHeading } from '../lib/categoryGroups'
import { useLanguage } from '../lib/LanguageContext'
import type { Lang } from '../lib/i18n'
import type { Category, Product, UnavailableBank } from '../lib/types'

interface CategoryPageProps {
  categories: Category[]
}

function formatUpdatedAt(iso: string, lang: Lang): string {
  const date = new Date(iso)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  const locale = lang === 'ru' ? 'ru-RU' : 'uz-UZ'
  const time = date.toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' })
  if (isToday) return `${lang === 'ru' ? 'сегодня' : 'bugun'}, ${time}`
  const day = date.toLocaleDateString(locale, { day: '2-digit', month: '2-digit' })
  return `${day}, ${time}`
}

export function CategoryPage({ categories }: CategoryPageProps) {
  const { categoryKey } = useParams<{ categoryKey: string }>()
  const { lang, t } = useLanguage()
  const [products, setProducts] = useState<Product[]>([])
  const [unavailableBanks, setUnavailableBanks] = useState<UnavailableBank[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!categoryKey) return
    let ignore = false

    async function loadProducts() {
      setIsLoading(true)
      try {
        const [data, unavailable] = await Promise.all([
          fetchProducts(categoryKey as string),
          fetchUnavailableBanks(categoryKey as string),
        ])
        if (ignore) return
        setProducts(data)
        setUnavailableBanks(unavailable)
        setError(null)
      } catch (err) {
        if (!ignore) setError(err instanceof Error ? err.message : "Mahsulotlarni yuklab bo'lmadi")
      } finally {
        if (!ignore) setIsLoading(false)
      }
    }

    loadProducts()
    return () => {
      ignore = true
    }
  }, [categoryKey])

  const activeCategoryData = categories.find((c) => c.key === categoryKey)
  const activeLabel = activeCategoryData
    ? getCategoryHeading(activeCategoryData.key, activeCategoryData.label, lang)
    : t('brandName')
  const lastUpdated =
    products.length > 0
      ? products.reduce((latest, p) => (p.scraped_at > latest ? p.scraped_at : latest), products[0].scraped_at)
      : null

  return (
    <>
      <div className="page-head">
        <div>
          <h1>{activeLabel}</h1>
          <p className="page-subtitle">{t('pageSubtitle')}</p>
        </div>
        {lastUpdated && (
          <span className="page-updated">
            <ClockIcon />
            {t('pulseUpdated')}: {formatUpdatedAt(lastUpdated, lang)}
          </span>
        )}
      </div>
      {error && <p className="error-state">{error}</p>}
      {!isLoading && <MarketPulse category={categoryKey ?? null} products={products} />}
      <ProductTable
        products={products}
        isLoading={isLoading}
        schema={activeCategoryData?.schema}
        category={categoryKey}
        unavailableBanks={unavailableBanks}
      />
    </>
  )
}
