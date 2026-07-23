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
