import type { Product } from './types'

export interface ProductColumn {
  key: string
  label: string
  render: (product: Product) => string
}

export function formatAmount(amount: number): string {
  const millions = Math.round((amount / 1_000_000) * 10) / 10
  return `${millions} mln so'm`
}

const downPaymentColumn: ProductColumn = {
  key: 'down_payment',
  label: "Boshlang'ich badal",
  render: (product) => (product.down_payment_pct !== null ? `${product.down_payment_pct}%` : '—'),
}

const gracePeriodColumn: ProductColumn = {
  key: 'grace_period',
  label: 'Imtiyozli davr',
  render: (product) => {
    if (product.grace_period_months === null) return '—'
    return product.grace_period_months > 0 ? 'Bor' : "Yo'q"
  },
}

const amountColumn: ProductColumn = {
  key: 'amount',
  label: 'Kredit miqdori',
  render: (product) => formatAmount(product.amount_max_som),
}

const specialTermsColumn: ProductColumn = {
  key: 'special_terms',
  label: 'Maxsus shartlari',
  render: (product) => product.special_terms ?? '—',
}

const paymentMethodColumn: ProductColumn = {
  key: 'payment_method',
  label: "To'lov usuli",
  render: (product) => product.payment_method ?? '—',
}

// Mikroqarz bo'limida to'lov usuli saytda aniq ko'rsatilmagan bank
// mahsulotlari uchun ikkala usul ("Annuitet, Differensial") ham taklif
// qilinadi deb hisoblanadi — noma'lum ("—") o'rniga shu ikkalasi ko'rsatiladi.
const mikroqarzPaymentMethodColumn: ProductColumn = {
  key: 'payment_method',
  label: "To'lov usuli",
  render: (product) => product.payment_method ?? 'Annuitet, Differensial',
}

const CREDIT_DOWN_PAYMENT_COLUMNS: ProductColumn[] = [
  downPaymentColumn,
  gracePeriodColumn,
  amountColumn,
  paymentMethodColumn,
]

const CREDIT_SPECIAL_TERMS_COLUMNS: ProductColumn[] = [
  amountColumn,
  gracePeriodColumn,
  specialTermsColumn,
  paymentMethodColumn,
]

// Mikroqarz (oflayn/onlayn) bo'limida "Maxsus shartlari" va "Imtiyozli
// davr" kolonkalari olib tashlangan.
const MIKROQARZ_COLUMNS: ProductColumn[] = [amountColumn, mikroqarzPaymentMethodColumn]

export function getProductColumns(schema: string | undefined, category?: string): ProductColumn[] {
  if (category === 'mikroqarz' || category === 'mikroqarz_onlayn') return MIKROQARZ_COLUMNS
  if (schema === 'credit_special_terms') return CREDIT_SPECIAL_TERMS_COLUMNS
  return CREDIT_DOWN_PAYMENT_COLUMNS
}
