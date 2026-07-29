import type {
  Category,
  ExplainProductRequest,
  ExplainProductResponse,
  Product,
  RecommendRequest,
  RecommendResponse,
  UnavailableBank,
} from './types'

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

export async function fetchRecommendation(request: RecommendRequest): Promise<RecommendResponse> {
  const response = await fetch(`${API_BASE_URL}/recommend`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`AI tavsiyasini olib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export function getExportExcelUrl(category: string, language: string): string {
  const url = new URL(`${API_BASE_URL}/export-excel`)
  url.searchParams.set('category', category)
  url.searchParams.set('language', language)
  return url.toString()
}

export function getExportAllExcelUrl(language: string): string {
  const url = new URL(`${API_BASE_URL}/export-excel-all`)
  url.searchParams.set('language', language)
  return url.toString()
}

export type TriggerScrapeStatus = 'started' | 'already_running' | 'error'

// 409 ("allaqachon ishlamoqda") kutilgan, oddiy holat — istisno (throw)
// emas, natija sifatida qaytariladi, shunda chaqiruvchi UI'da alohida
// (xatolik emas, oddiy ogohlantirish) matn ko'rsata oladi.
export async function triggerScrapeRefresh(): Promise<TriggerScrapeStatus> {
  const response = await fetch(`${API_BASE_URL}/trigger-scrape`, { method: 'POST' })
  if (response.status === 409) return 'already_running'
  if (!response.ok) return 'error'
  return 'started'
}

export async function fetchProductExplanation(request: ExplainProductRequest): Promise<ExplainProductResponse> {
  const response = await fetch(`${API_BASE_URL}/explain-product`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (!response.ok) {
    throw new Error(`AI izohini olib bo'lmadi: ${response.status}`)
  }
  return response.json()
}
