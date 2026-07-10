import { useEffect, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ProductTable } from './components/ProductTable'
import { RecommendPanel } from './components/RecommendPanel'
import { fetchCategories, fetchProducts } from './lib/api'
import type { Category, Product } from './lib/types'

export function App() {
  const [categories, setCategories] = useState<Category[]>([])
  const [activeCategory, setActiveCategory] = useState<string | null>(null)
  const [products, setProducts] = useState<Product[]>([])
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
    setError(null)
    fetchProducts(activeCategory)
      .then((data) => {
        if (!ignore) setProducts(data)
      })
      .catch((err) => {
        if (!ignore) setError(err instanceof Error ? err.message : "Mahsulotlarni yuklab bo'lmadi")
      })
    return () => {
      ignore = true
    }
  }, [activeCategory])

  const activeCategoryData = categories.find((c) => c.key === activeCategory)
  const activeLabel = activeCategoryData?.label ?? 'Bozor Tahlili'

  return (
    <div className="app-shell">
      <Sidebar categories={categories} activeCategory={activeCategory} onSelect={setActiveCategory} />
      <main className="main-content">
        <h1>{activeLabel}</h1>
        {error && <p className="error-state">{error}</p>}
        <ProductTable products={products} schema={activeCategoryData?.schema} />
        {activeCategory && <RecommendPanel category={activeCategory} />}
      </main>
    </div>
  )
}
