import type { Category, Product, UnavailableBank } from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function fetchCategories(): Promise<Category[]> {
  const response = await fetch(`${API_BASE_URL}/categories`)
  if (!response.ok) {
    throw new Error(`Kategoriyalarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchProducts(category: string): Promise<Product[]> {
  const url = new URL(`${API_BASE_URL}/products`)
  url.searchParams.set('category', category)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Mahsulotlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchUnavailableBanks(category: string): Promise<UnavailableBank[]> {
  const url = new URL(`${API_BASE_URL}/unavailable-banks`)
  url.searchParams.set('category', category)
  const response = await fetch(url)
  if (!response.ok) {
    throw new Error(`Mavjud bo'lmagan banklar ro'yxatini yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}
