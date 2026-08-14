import { useEffect, useState } from 'react'
import type { Product } from '../lib/types'
import { isHouseBank } from '../lib/bank'
import { getBankLogo } from '../lib/bankLogos'
import { formatAmount, formatPaymentMethod } from '../lib/productColumns'
import { fetchProductExplanation } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { translate, type Lang } from '../lib/i18n'
import robotIcon from '../assets/icons/robot_icon_badge.png'

interface MarketPulseProps {
  category: string | null
  products: Product[]
  updatedLabel: string | null
}

// Jadval ham (ProductTable) aynan shu tartibda saralaydi: eng past
// rate_min birinchi. "Eng zo'r taklif" kartochkasi shu bilan bir xil
// tanlovni ishlatishi SHART — aks holda kartochka jadvaldagi 1-qatordan
// boshqa bankni ko'rsatib, chalkashlik keltirib chiqaradi.
function pickFeatured(products: Product[]): Product {
  return [...products].sort((a, b) => a.rate_min - b.rate_min)[0]
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

function formatTermRange(product: Product, lang: Lang): string {
  const unit = translate(lang, 'monthUnit')
  return product.term_min_months === product.term_max_months
    ? `${product.term_min_months} ${unit}`
    : `${product.term_min_months}–${product.term_max_months} ${unit}`
}

// Bozorni ikki qismga bo'lib tushuntiruvchi jumla quradi: eng past stavkada
// nechta bank turibdi (barobar bo'lsa) va qolganlar qaysi oraliqda
// raqobatlashmoqda. Sabab (masalan "dilerlik aksiyasi") taxmin qilinmaydi —
// faqat ma'lumotning o'zidan kelib chiqadigan haqiqatlar aytiladi, chunki bu
// matn har qanday kategoriya (avtokredit, mikroqarz va h.k.) uchun ishlaydi.
function buildInsight(lang: Lang, bankRates: BankRate[], sqbRank: number): string {
  const minRate = bankRates[0].rate
  const tiedBest = bankRates.filter((entry) => entry.rate === minRate)
  const rest = bankRates.filter((entry) => entry.rate > minRate)

  if (lang === 'ru') {
    const leadSentence =
      tiedBest.length > 1
        ? `${tiedBest.length} из ${bankRates.length} банков предлагают самую низкую ставку ${formatRate(minRate)}.`
        : `Самую низкую ставку предлагает ${tiedBest[0].bank} — ${formatRate(minRate)}.`

    const restSentence =
      rest.length > 0
        ? rest.length === 1
          ? `Остался один банк со ставкой ${formatRate(rest[0].rate)}.`
          : `Остальные ${rest.length} банков конкурируют в диапазоне ${formatRate(rest[0].rate)}–${formatRate(rest[rest.length - 1].rate)}.`
        : ''

    const rankSentence = sqbRank > 0 ? `SQB — ${sqbRank}-е место из ${bankRates.length} банков.` : ''

    return [leadSentence, restSentence, rankSentence].filter(Boolean).join(' ')
  }

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
  const { lang, t } = useLanguage()
  const [aiText, setAiText] = useState<string | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [isAiLoading, setIsAiLoading] = useState(false)

  useEffect(() => {
    if (!category || products.length === 0) {
      setAiText(null)
      setAiError(null)
      return
    }

    // Kartochka (pastda) qaysi mahsulotni ko'rsatsa, AI ANIQ shu haqida
    // yozadi — mustaqil ranking/ballash ishlatilmaydi, shuning uchun
    // ikkalasi hech qachon boshqa-boshqa bankni ko'rsatib qolmaydi.
    const featured = pickFeatured(products)
    let ignore = false
    setIsAiLoading(true)
    setAiError(null)

    fetchProductExplanation({
      category,
      bank: featured.bank,
      product_name: featured.product_name,
      rate_min: featured.rate_min,
      rate_max: featured.rate_max,
      term_min_months: featured.term_min_months,
      term_max_months: featured.term_max_months,
      amount_max_som: featured.amount_max_som,
      requires_collateral: featured.requires_collateral,
      down_payment_pct: featured.down_payment_pct,
      language: lang,
    })
      .then((data) => {
        if (ignore) return
        setAiText(data.explanation)
      })
      .catch((err) => {
        if (ignore) return
        setAiError(err instanceof Error ? err.message : "AI izohini olib bo'lmadi")
      })
      .finally(() => {
        if (!ignore) setIsAiLoading(false)
      })

    return () => {
      ignore = true
    }
  }, [category, products, lang])

  if (products.length === 0) return null

  const bankRates = cheapestPerBank(products)
  const sqbRank = bankRates.findIndex((entry) => isHouseBank(entry.bank)) + 1
  const insight = buildInsight(lang, bankRates, sqbRank)

  const featured = pickFeatured(products)
  const featuredLogo = getBankLogo(featured.bank)
  const featuredIsHouse = isHouseBank(featured.bank)

  return (
    <section className="market-pulse" aria-label={t('pulseEyebrow')}>
      <div className="pulse-featured">
        <div className="pulse-featured-head">
          <span className="market-pulse-eyebrow">{t('pulseEyebrow')}</span>
          <div className="market-pulse-meta">
            <div className="meta-chip">
              <span className="meta-chip-value">{bankRates.length}</span>
              <span className="meta-chip-label">{t('pulseBankCount')}</span>
            </div>
            {updatedLabel && (
              <div className="meta-chip">
                <span className="meta-chip-value meta-chip-time">{updatedLabel}</span>
                <span className="meta-chip-label">{t('pulseUpdated')}</span>
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
                {featuredIsHouse && <span className="house-flag">{t('houseFlag')}</span>}
              </span>
              <span className="pulse-featured-product-name">{featured.product_name}</span>
            </div>
          </div>

          <div className="pulse-featured-stats">
            <div className="pulse-stat pulse-stat-rate">
              <span className="pulse-stat-value">{formatRateRange(featured)}</span>
              <span className="pulse-stat-label">{t('pulseRate')}</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{formatTermRange(featured, lang)}</span>
              <span className="pulse-stat-label">{t('pulseTerm')}</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{formatAmount(featured.amount_max_som, lang)}</span>
              <span className="pulse-stat-label">{t('pulseAmount')}</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{featured.requires_collateral ? t('yes') : t('no')}</span>
              <span className="pulse-stat-label">{t('pulseCollateral')}</span>
            </div>
            <div className="pulse-stat">
              <span className="pulse-stat-value">{formatPaymentMethod(featured.payment_method, lang)}</span>
              <span className="pulse-stat-label">{t('pulsePaymentMethod')}</span>
            </div>
          </div>
        </div>

        {sqbRank > 0 && (
          <p className="market-pulse-rank">
            {lang === 'ru' ? (
              <>
                SQB — <strong>{sqbRank}</strong>-е место из <strong>{bankRates.length}</strong> банков
              </>
            ) : (
              <>
                SQB — <strong>{bankRates.length}</strong> bankdan <strong>{sqbRank}</strong>-o'rinda
              </>
            )}
          </p>
        )}

        <div className="pulse-ai-note">
          <span className="pulse-ai-badge">
            <img src={robotIcon} alt={t('pulseAiBadge')} className="pulse-ai-badge-icon" />
          </span>
          {isAiLoading && <span className="pulse-ai-text pulse-ai-text-muted">{t('pulseAiLoading')}</span>}
          {!isAiLoading && aiError && <span className="pulse-ai-text pulse-ai-text-muted">{aiError}</span>}
          {!isAiLoading && !aiError && aiText && <span className="pulse-ai-text">{aiText}</span>}
        </div>
      </div>

      <p className="market-pulse-insight">{insight}</p>
    </section>
  )
}
