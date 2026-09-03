export interface Category {
  key: string
  label: string
  schema: string
}

export interface UnavailableBank {
  bank: string
  reason: string
}

export interface RecommendRequest {
  category: string
  amount_som: number
  term_months: number
  collateral_ok: boolean
}

export interface RecommendedItem {
  bank: string
  product_name: string
  score: number
  rate_min: number
  rate_max: number
  term_min_months: number
  term_max_months: number
  amount_max_som: number
  requires_collateral: boolean
  down_payment_pct: number | null
  payment_method: string | null
  grace_period_months: number | null
}

export interface RecommendResponse {
  recommendations: RecommendedItem[]
  explanation: string
}

export interface ExplainProductRequest {
  category: string
  bank: string
  product_name: string
  rate_min: number
  rate_max: number
  term_min_months: number
  term_max_months: number
  amount_max_som: number
  requires_collateral: boolean
  down_payment_pct: number | null
  language?: 'uz' | 'ru'
}

export interface ExplainProductResponse {
  explanation: string
}

export interface Product {
  bank: string
  category: string
  product_name: string
  rate_min: number
  rate_max: number
  term_min_months: number
  term_max_months: number
  amount_max_som: number
  requires_collateral: boolean
  down_payment_pct: number | null
  grace_period_months: number | null
  payment_method: string | null
  special_terms: string | null
  scraped_at: string
}

export type UserRole = 'admin' | 'user'

export interface AuthUser {
  username: string
  role: UserRole
}

export interface LoginResponse {
  access_token: string
  username: string
  role: UserRole
}

export interface AdminUser {
  id: number
  username: string
  role: UserRole
  created_at: string
}

export interface CreateUserRequest {
  username: string
  password: string
  role: UserRole
}

export interface UpdateUserRequest {
  username?: string
  password?: string
  role?: UserRole
}

export type ScrapeRunStatus = 'success' | 'failed' | 'running' | 'never_run'

export interface ScrapeRun {
  bank: string
  status: ScrapeRunStatus
  started_at: string | null
  finished_at: string | null
  error_message: string | null
  products_found: number
}
