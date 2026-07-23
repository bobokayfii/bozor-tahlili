import { useEffect, useState } from 'react'
import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { formatAmount } from '../lib/productColumns'
import { fetchRecommendation } from '../lib/api'

interface MarketPulseProps {
  category: string | null
  products: Product[]
  updatedLabel: string | null
}

// Foydalanuvchidan mezon so'ralmaydi (bu — avtomatik "bozor pulsi" ko'rinishi,
// forma emas), shuning uchun /recommend uchun mezon joriy kategoriyadagi
// mahsulotlarning o'zidan chiqariladi: eng qisqa muddat talabi (barcha
// mahsulotlar mos kelishi uchun mavjud minimal muddatlarning eng kattasi) va
// eng kichik maksimal summa (hech bir bankning chegarasidan oshmasligi uchun).
function deriveCriteria(products: Product[]) {
  const termMonths = Math.max(...products.map((p) => p.term_min_months))
  const amountSom = Math.min(...products.map((p) => p.amount_max_som))
  return { amount_som: amountSom, term_months: termMonths, collateral_ok: true }
}

interface BankRate {
  bank: string
  rate: number
}

function cheapestPerBank(products: Product[]): BankRate[] {
  const best = new Map<string, number>()
  for (const product of products) {
    const current = best.get(product.bank)
    if (current === undefined || product.rate_min < current) {
      best.set(product.bank, product.rate_min)
    }
  }
  return [...best.entries()].map(([bank, rate]) => ({ bank, rate })).sort((a, b) => a.rate - b.rate)
}

function formatRate(rate: number): string {
  return `${rate}%`
}

function formatRateRange(product: Product): string {
  return product.rate_min === product.rate_max
    ? formatRate(product.rate_min)
    : `${formatRate(product.rate_min)} – ${formatRate(product.rate_max)}`
}

function formatTermRange(product: Product): string {
  return product.term_min_months === product.term_max_months
    ? `${product.term_min_months} oy`
    : `${product.term_min_months}–${product.term_max_months} oy`
}

// Bozorni ikki qismga bo'lib tushuntiruvchi jumla quradi: eng past stavkada
// nechta bank turibdi (barobar bo'lsa) va qolganlar qaysi oraliqda
// raqobatlashmoqda. Sabab (masalan "dilerlik aksiyasi") taxmin qilinmaydi —
// faqat ma'lumotning o'zidan kelib chiqadigan haqiqatlar aytiladi, chunki bu
// matn har qanday kategoriya (avtokredit, mikroqarz va h.k.) uchun ishlaydi.
function buildInsight(bankRates: BankRate[], sqbRank: number): string {
  const minRate = bankRates[0].rate
  const tiedBest = bankRates.filter((entry) => entry.rate === minRate)
  const rest = bankRates.filter((entry) => entry.rate > minRate)

  const leadSentence =
    tiedBest.length > 1
      ? `${bankRates.length} bankdan ${tiedBest.length} tasi eng past ${formatRate(minRate)} stavkani taklif qilmoqda.`
      : `Eng past stavkani ${tiedBest[0].bank} — ${formatRate(minRate)} miqdorida taklif qilmoqda.`

  const restSentence =
    rest.length > 0
      ? rest.length === 1
        ? `Qolgan bitta bank ${formatRate(rest[0].rate)} stavkada turibdi.`
        : `Qolgan ${rest.length} bank ${formatRate(rest[0].rate)}–${formatRate(rest[rest.length - 1].rate)} oralig'ida raqobatlashmoqda.`
      : ''

  const rankSentence = sqbRank > 0 ? `SQB — ${bankRates.length} bankdan ${sqbRank}-o'rinda.` : ''

  return [leadSentence, restSentence, rankSentence].filter(Boolean).join(' ')
}

export function MarketPulse({ category, products, updatedLabel }: MarketPulseProps) {
  const [aiText, setAiText] = useState<string | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [isAiLoading, setIsAiLoading] = useState(false)

  useEffect(() => {
    if (!category || products.length === 0) {
      setAiText(null)
      setAiError(null)
      return
    }

    let ignore = false
    setIsAiLoading(true)
    setAiError(null)

    fetchRecommendation({ category, ...deriveCriteria(products) })
      .then((data) => {
        if (ignore) return
        setAiText(data.explanation)
      })
      .catch((err) => {
        if (ignore) return
        setAiError(err instanceof Error ? err.message : "AI tavsiyasini olib bo'lmadi")
      })
      .finally(() => {
        if (!ignore) setIsAiLoading(false)
      })

    return () => {
      ignore = true
    }
  }, [category, products])

  if (products.length === 0) return null

  const bankRates = cheapestPerBank(products)
  const sqbRank = bankRates.findIndex((entry) => isHouseBank(entry.bank)) + 1
  const insight = buildInsight(bankRates, sqbRank)

  // "Eng zo'r mahsulot" — hozircha faqat eng past stavka bo'yicha tanlanadi
  // (oddiy, tushunarli mezon). Teng bo'lsa, ro'yxatdagi birinchisi olinadi.
  const featured = [...products].sort((a, b) => a.rate_min - b.rate_min)[0]
  const featuredLogo = getBankLogo(featured.bank)
  const featuredIsHouse = isHouseBank(featured.bank)

  return (
    <section className="market-pulse" aria-label="Bozor pulsi">
      <div className="pulse-featured">
        <div className="pulse-featured-head">
          <span className="market-pulse-eyebrow">Bozor pulsi · Eng zo'r taklif</span>
          <div className="market-pulse-meta">
            <div className="meta-chip">
              <span className="meta-chip-value">{bankRates.length}</span>
              <span className="meta-chip-label">Bank</span>
            </div>
            {updatedLabel && (
              <div className="meta-chip">
                <span className="meta-chip-value meta-chip-time">{updatedLabel}</span>
                <span className="meta-chip-label">Yangilangan</span>
              </div>
            )}
          </div>
        </div>

        <div className="pulse-featured-body">
          <div className="pulse-featured-bank">
            {featuredLogo && <img src={featuredLogo} alt="" className="pulse-featured-logo" />}
            <div className="pulse-featured-names">
              <span className="pulse-featured-bank-name">
                {featured.bank}
                {featuredIsHouse && <span className="house-flag">Biz</span>}
              </span>
              <span className="pulse-featured-product-name">{featured.product_name}</span>
            </div>
          </div>

          <div className="pulse-featured-stats">
            <div className="pulse-stat pulse-stat-rate">
              <span className="pulse-stat-value">{formatRateRange(featured)}</span>
              <span className="pulse-stat-label">Stavka</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{formatTermRange(featured)}</span>
              <span className="pulse-stat-label">Muddat</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{formatAmount(featured.amount_max_som)}</span>
              <span className="pulse-stat-label">Kredit miqdori</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{featured.requires_collateral ? 'Bor' : "Yo'q"}</span>
              <span className="pulse-stat-label">Garov</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{featured.payment_method ?? '—'}</span>
              <span className="pulse-stat-label">To'lov usuli</span>
            </div>
          </div>
        </div>

        {sqbRank > 0 && (
          <p className="market-pulse-rank">
            SQB — <strong>{bankRates.length}</strong> bankdan <strong>{sqbRank}</strong>-o'rinda
          </p>
        )}
      </div>

      <div className="pulse-ai-teaser">
        <span className="pulse-ai-badge">AI</span>
        <div className="pulse-ai-copy">
          <span className="pulse-ai-title">AI tavsiyasi</span>
          {isAiLoading && <p className="pulse-ai-text">Tahlil qilinmoqda...</p>}
          {!isAiLoading && aiError && <p className="pulse-ai-text">{aiError}</p>}
          {!isAiLoading && !aiError && aiText && <p className="pulse-ai-text">{aiText}</p>}
        </div>
      </div>

      <p className="market-pulse-insight">{insight}</p>
    </section>
  )
}
