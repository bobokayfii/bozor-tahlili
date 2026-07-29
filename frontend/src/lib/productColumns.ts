import type { Product } from './types'
import { translate, type Lang } from './i18n'

export interface ProductColumn {
  key: string
  label: string
  render: (product: Product) => string
}

export function formatAmount(amount: number, lang: Lang = 'uz'): string {
  const millions = Math.round((amount / 1_000_000) * 10) / 10
  return lang === 'ru' ? `${millions} млн сум` : `${millions} mln so'm`
}

// Bank sahifalaridan olingan to'lov usuli qiymatlari doim shu uchta Uzbek/
// neytral atamadan biri ("Annuitet"/"Differensial"/ikkalasi) — ruscha
// interfeys uchun shu bir nechta ma'lum qiymat tarjima qilinadi, tanilmagan
// qiymat esa o'zgarishsiz qoladi.
const PAYMENT_METHOD_RU: Record<string, string> = {
  Annuitet: 'Аннуитет',
  Differensial: 'Дифференцированный',
  'Annuitet, Differensial': 'Аннуитет, Дифференцированный',
}

export function translatePaymentMethod(value: string, lang: Lang): string {
  if (lang !== 'ru') return value
  return PAYMENT_METHOD_RU[value] ?? value
}

export function formatPaymentMethod(paymentMethod: string | null, lang: Lang): string {
  return paymentMethod === null ? translate(lang, 'defaultPaymentMethod') : translatePaymentMethod(paymentMethod, lang)
}

function downPaymentColumn(lang: Lang): ProductColumn {
  return {
    key: 'down_payment',
    label: translate(lang, 'tableDownPayment'),
    render: (product) => (product.down_payment_pct !== null ? `${product.down_payment_pct}%` : translate(lang, 'dash')),
  }
}

function gracePeriodColumn(lang: Lang): ProductColumn {
  return {
    key: 'grace_period',
    label: translate(lang, 'tableGracePeriod'),
    render: (product) => {
      if (product.grace_period_months === null) return translate(lang, 'no')
      return product.grace_period_months > 0 ? translate(lang, 'yes') : translate(lang, 'no')
    },
  }
}

function amountColumn(lang: Lang): ProductColumn {
  return {
    key: 'amount',
    label: translate(lang, 'tableAmount'),
    render: (product) => formatAmount(product.amount_max_som, lang),
  }
}

function specialTermsColumn(lang: Lang): ProductColumn {
  return {
    key: 'special_terms',
    label: translate(lang, 'tableSpecialTerms'),
    render: (product) => product.special_terms ?? translate(lang, 'dash'),
  }
}

// Sahifada to'lov usuli aniq ko'rsatilmagan bank mahsulotlari uchun
// ikkala usul ("Annuitet, Differensial") ham taklif qilinadi deb
// hisoblanadi — noma'lum ("—") o'rniga shu ikkalasi ko'rsatiladi.
function paymentMethodColumn(lang: Lang): ProductColumn {
  return {
    key: 'payment_method',
    label: translate(lang, 'tablePaymentMethod'),
    render: (product) => formatPaymentMethod(product.payment_method, lang),
  }
}

export function getProductColumns(schema: string | undefined, category?: string, lang: Lang = 'uz'): ProductColumn[] {
  // Mikroqarz (oflayn/onlayn) bo'limida "Maxsus shartlari" va "Imtiyozli
  // davr" kolonkalari olib tashlangan.
  if (category === 'mikroqarz' || category === 'mikroqarz_onlayn') {
    return [amountColumn(lang), paymentMethodColumn(lang)]
  }
  if (schema === 'credit_special_terms') {
    return [amountColumn(lang), gracePeriodColumn(lang), specialTermsColumn(lang), paymentMethodColumn(lang)]
  }
  return [downPaymentColumn(lang), gracePeriodColumn(lang), amountColumn(lang), paymentMethodColumn(lang)]
}
