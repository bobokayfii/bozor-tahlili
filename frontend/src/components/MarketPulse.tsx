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
}

// Jadval ham (ProductTable) aynan shu tartibda saralaydi: eng past
// rate_min birinchi. "Eng zo'r taklif" kartochkasi shu bilan bir xil
// tanlovni ishlatishi SHART — aks holda kartochka jadvaldagi 1-qatordan
// boshqa bankni ko'rsatib, chalkashlik keltirib chiqaradi.
function pickFeatured(products: Product[]): Product {
  return [...products].sort((a, b) => a.rate_min - b.rate_min)[0]
}

// AI javobi backend/LLM tomonidan erkin matn sifatida kelgani uchun uzun
// tire (—/–) ishlatib qo'yishi mumkin — saytda faqat oddiy tire ko'rinishi
// uchun bu yerda tozalanadi.
function normalizeDashes(text: string): string {
  return text.replace(/[—–]/g, '-')
}

function formatRate(rate: number): string {
  return `${rate}%`
}

function formatRateRange(product: Product): string {
  return product.rate_min === product.rate_max
    ? formatRate(product.rate_min)
    : `${formatRate(product.rate_min)} - ${formatRate(product.rate_max)}`
}

function formatTermRange(product: Product, lang: Lang): string {
  const unit = translate(lang, 'monthUnit')
  return product.term_min_months === product.term_max_months
    ? `${product.term_min_months} ${unit}`
    : `${product.term_min_months}-${product.term_max_months} ${unit}`
}

export function MarketPulse({ category, products }: MarketPulseProps) {
  const { lang, t } = useLanguage()
  const [aiText, setAiText] = useState<string | null>(null)
  const [aiError, setAiError] = useState<string | null>(null)
  const [isAiLoading, setIsAiLoading] = useState(false)

  useEffect(() => {
    if (!category || products.length === 0) {
      // Resets state ahead of an async outcome, not deriving it from props
      // during render - the featured product genuinely changes async (a
      // fetch keyed on it follows below), so this can't move out of the effect.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAiText(null)
      setAiError(null)
      return
    }

    // Kartochka (pastda) qaysi mahsulotni ko'rsatsa, AI ANIQ shu haqida
    // yozadi — mustaqil ranking/ballash ishlatilmaydi, shuning uchun
    // ikkalasi hech qachon boshqa-boshqa bankni ko'rsatib qolmaydi.
    const featured = pickFeatured(products)
    let ignore = false
    const controller = new AbortController()
    setIsAiLoading(true)
    setAiError(null)

    fetchProductExplanation(
      {
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
      },
      controller.signal,
    )
      .then((data) => {
        if (ignore) return
        setAiText(normalizeDashes(data.explanation))
      })
      .catch((err) => {
        if (ignore) return
        setAiError(err instanceof Error ? err.message : "AI izohini olib bo'lmadi")
      })
      .finally(() => {
        if (!ignore) setIsAiLoading(false)
      })

    return () => {
      controller.abort()
      ignore = true
    }
  }, [category, products, lang])

  if (products.length === 0) return null

  const featured = pickFeatured(products)
  const featuredLogo = getBankLogo(featured.bank)
  const featuredIsHouse = isHouseBank(featured.bank)

  return (
    <section className="market-pulse" aria-label={t('pulseEyebrow')}>
      <div className="pulse-featured">
        <div className="pulse-featured-head">
          <span className="market-pulse-eyebrow">{t('pulseEyebrow')}</span>
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

        <div className="pulse-ai-note">
          <span className="pulse-ai-badge">
            <img src={robotIcon} alt={t('pulseAiBadge')} className="pulse-ai-badge-icon" />
          </span>
          <div className="pulse-ai-body">
            <span className="pulse-ai-label">{t('pulseAiLabel')}</span>
            {isAiLoading && <span className="pulse-ai-text pulse-ai-text-muted">{t('pulseAiLoading')}</span>}
            {!isAiLoading && aiError && <span className="pulse-ai-text pulse-ai-text-muted">{aiError}</span>}
            {!isAiLoading && !aiError && aiText && <span className="pulse-ai-text">{aiText}</span>}
          </div>
        </div>
      </div>
    </section>
  )
}
