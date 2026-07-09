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

  useEffect(() => {
    fetchCategories().then((data) => {
      setCategories(data)
      if (data.length > 0) {
        setActiveCategory(data[0].key)
      }
    })
  }, [])

  useEffect(() => {
    if (!activeCategory) return
    fetchProducts(activeCategory).then(setProducts)
  }, [activeCategory])

  const activeLabel = categories.find((c) => c.key === activeCategory)?.label ?? 'Bozor Tahlili'

  return (
    <div className="app-shell">
      <Sidebar categories={categories} activeCategory={activeCategory} onSelect={setActiveCategory} />
      <main className="main-content">
        <h1>{activeLabel}</h1>
        <ProductTable products={products} />
        {activeCategory && <RecommendPanel category={activeCategory} />}
      </main>
    </div>
  )
}
