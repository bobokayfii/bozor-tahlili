import type {
  AdminUser,
  AuthUser,
  Category,
  CreateUserRequest,
  ExplainProductRequest,
  ExplainProductResponse,
  LoginResponse,
  Product,
  RecommendRequest,
  RecommendResponse,
  ScrapeRun,
  UnavailableBank,
  UpdateUserRequest,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_STORAGE_KEY = 'bozor-tahlili-token'

let onUnauthorized: (() => void) | null = null

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler
}

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY)
}

export function setToken(token: string): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export function clearToken(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY)
}

function authHeaders(): Record<string, string> {
  const token = getToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

// Login'dan boshqa BARCHA so'rovlar shu orqali o'tadi — Authorization
// header'ni avtomatik qo'shadi va 401 kelsa (token yaroqsiz/muddati
// tugagan) tokenni tozalab, AuthContext'ga xabar beradi.
async function apiFetch(input: string | URL, init: RequestInit = {}): Promise<Response> {
  const response = await fetch(input, {
    ...init,
    headers: { ...authHeaders(), ...init.headers },
  })
  if (response.status === 401) {
    clearToken()
    onUnauthorized?.()
  }
  return response
}

export async function login(username: string, password: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
  if (response.status === 429) {
    // Distinct from a plain wrong-password 401 so the UI doesn't tell
    // someone their (possibly correct) password is wrong when they're
    // actually rate-limited (api/main.py's login rate limiter).
    throw new Error('RATE_LIMITED')
  }
  if (!response.ok) {
    throw new Error("Login yoki parol noto'g'ri")
  }
  return response.json()
}

export async function fetchCurrentUser(): Promise<AuthUser> {
  const response = await apiFetch(`${API_BASE_URL}/auth/me`)
  if (!response.ok) {
    throw new Error(`Sessiyani tekshirib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchUsers(): Promise<AdminUser[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`)
  if (!response.ok) {
    throw new Error(`Userlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchScrapeRuns(): Promise<ScrapeRun[]> {
  const response = await apiFetch(`${API_BASE_URL}/admin/scrape-runs`)
  if (!response.ok) {
    throw new Error(`Scraper holatini yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function createUser(request: CreateUserRequest): Promise<AdminUser> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (response.status === 409) {
    throw new Error('USERNAME_TAKEN')
  }
  if (response.status === 422) {
    throw new Error('PASSWORD_TOO_SHORT')
  }
  if (!response.ok) {
    throw new Error(`Userni qo'shib bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function updateUser(id: number, request: UpdateUserRequest): Promise<AdminUser> {
  const response = await apiFetch(`${API_BASE_URL}/admin/users/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  })
  if (response.status === 409) {
    throw new Error('USERNAME_TAKEN')
  }
  if (response.status === 400) {
    throw new Error('SELF_DEMOTE')
  }
  if (response.status === 422) {
    throw new Error('PASSWORD_TOO_SHORT')
  }
  if (!response.ok) {
    throw new Error(`Userni yangilab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchCategories(): Promise<Category[]> {
  const response = await apiFetch(`${API_BASE_URL}/categories`)
  if (!response.ok) {
    throw new Error(`Kategoriyalarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchProducts(category: string, signal?: AbortSignal): Promise<Product[]> {
  const url = new URL(`${API_BASE_URL}/products`)
  url.searchParams.set('category', category)
  const response = await apiFetch(url, { signal })
  if (!response.ok) {
    throw new Error(`Mahsulotlarni yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchUnavailableBanks(category: string, signal?: AbortSignal): Promise<UnavailableBank[]> {
  const url = new URL(`${API_BASE_URL}/unavailable-banks`)
  url.searchParams.set('category', category)
  const response = await apiFetch(url, { signal })
  if (!response.ok) {
    throw new Error(`Mavjud bo'lmagan banklar ro'yxatini yuklab bo'lmadi: ${response.status}`)
  }
  return response.json()
}

export async function fetchRecommendation(request: RecommendRequest): Promise<RecommendResponse> {
  const response = await apiFetch(`${API_BASE_URL}/recommend`, {
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

// Export endpointlari endi autentifikatsiya talab qilgani uchun oddiy
// <a href> yetarli emas (brauzer navigatsiyasi Authorization header
// yubormaydi) — shu sabab fetch orqali blob sifatida yuklab olinadi va
// vaqtinchalik <a download> orqali saqlashga uzatiladi.
export async function downloadFile(url: string, filename: string): Promise<void> {
  const response = await apiFetch(url)
  if (!response.ok) {
    throw new Error(`Faylni yuklab olib bo'lmadi: ${response.status}`)
  }
  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(objectUrl)
}

export type TriggerScrapeStatus = 'started' | 'already_running' | 'error'

export async function triggerScrapeRefresh(): Promise<TriggerScrapeStatus> {
  const response = await apiFetch(`${API_BASE_URL}/trigger-scrape`, { method: 'POST' })
  if (response.status === 409) return 'already_running'
  if (!response.ok) return 'error'
  return 'started'
}

export async function fetchProductExplanation(
  request: ExplainProductRequest,
  signal?: AbortSignal,
): Promise<ExplainProductResponse> {
  const response = await apiFetch(`${API_BASE_URL}/explain-product`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
    signal,
  })
  if (!response.ok) {
    throw new Error(`AI izohini olib bo'lmadi: ${response.status}`)
  }
  return response.json()
}
