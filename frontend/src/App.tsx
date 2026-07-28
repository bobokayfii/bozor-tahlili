import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ProductTable } from './components/ProductTable'
import { MarketPulse } from './components/MarketPulse'
import { fetchCategories, fetchProducts, fetchUnavailableBanks } from './lib/api'
import { getCategoryHeading } from './lib/categoryGroups'
import { useLanguage } from './lib/LanguageContext'
import type { Lang } from './lib/i18n'
import type { Category, Product, UnavailableBank } from './lib/types'
import logo from './assets/logo.png'

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

function LanguageToggle() {
  const { lang, setLang } = useLanguage()
  return (
    <div className="lang-toggle" role="group" aria-label="Til / Язык">
      <button
        type="button"
        className={lang === 'uz' ? 'lang-toggle-btn active' : 'lang-toggle-btn'}
        onClick={() => setLang('uz')}
      >
        UZ
      </button>
      <button
        type="button"
        className={lang === 'ru' ? 'lang-toggle-btn active' : 'lang-toggle-btn'}
        onClick={() => setLang('ru')}
      >
        RU
      </button>
    </div>
  )
}

export function App() {
  const { lang, t } = useLanguage()
  const [categories, setCategories] = useState<Category[]>([])
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])
  const [unavailableBanks, setUnavailableBanks] = useState<UnavailableBank[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCategories()
      .then((data) => {
        setCategories(data)
        if (data.length > 0) {
          setActiveCategory(data[0].key)
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Kategoriyalarni yuklab bo'lmadi")
      })
  }, [])

  useEffect(() => {
    if (!activeCategory) return
    let ignore = false

    async function loadProducts() {
      setIsLoading(true)
      try {
        const [data, unavailable] = await Promise.all([
          fetchProducts(activeCategory as string),
          fetchUnavailableBanks(activeCategory as string),
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
  }, [activeCategory])

  const activeCategoryData = categories.find((c) => c.key === activeCategory)
  const activeLabel = activeCategoryData
    ? getCategoryHeading(activeCategoryData.key, activeCategoryData.label, lang)
    : 'Bozor Tahlili'
  const lastUpdated =
    products.length > 0
      ? products.reduce((latest, p) => (p.scraped_at > latest ? p.scraped_at : latest), products[0].scraped_at)
      : null

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-brand">
          <img src={logo} alt="Bozor Tahlili" className="app-topbar-logo" />
        </div>
        <LanguageToggle />
      </header>
      <div className="app-body">
        <Sidebar categories={categories} activeCategory={activeCategory} onSelect={setActiveCategory} />
        <main className="main-content">
          <div className="page-head">
            <div>
              <h1>{activeLabel}</h1>
              <p className="page-subtitle">{t('pageSubtitle')}</p>
            </div>
          </div>
          {error && <p className="error-state">{error}</p>}
          {!isLoading && (
            <MarketPulse
              category={activeCategory}
              products={products}
              updatedLabel={lastUpdated && formatUpdatedAt(lastUpdated, lang)}
            />
          )}
          <ProductTable
            products={products}
            isLoading={isLoading}
            schema={activeCategoryData?.schema}
            category={activeCategory ?? undefined}
            unavailableBanks={unavailableBanks}
          />
        </main>
      </div>
    </div>
  )
}
