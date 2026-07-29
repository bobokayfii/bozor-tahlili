import carIcon from '../assets/icons/car.png'
import crownIcon from '../assets/icons/crown.png'
import flashCircleIcon from '../assets/icons/flash-circle.png'
import walletIcon from '../assets/icons/wallet.png'
import cardIcon from '../assets/icons/card.png'
import moneyIcon from '../assets/icons/money.png'
import houseIcon from '../assets/icons/house.png'
import type { Lang } from './i18n'

export interface CategoryGroup {
  label: string
  labelRu: string
  icon: string
  iconColor: string
  keys: string[]
  shortLabels?: Record<string, string>
  shortLabelsRu?: Record<string, string>
}

export const CATEGORY_GROUPS: CategoryGroup[] = [
  {
    label: 'Avtokredit',
    labelRu: 'Автокредит',
    icon: carIcon,
    iconColor: '#c2703a',
    keys: ['avtokredit', 'avtokredit_ikkilamchi'],
    shortLabels: {
      avtokredit: 'Birlamchi bozor',
      avtokredit_ikkilamchi: 'Ikkilamchi bozor',
    },
    shortLabelsRu: {
      avtokredit: 'Первичный рынок',
      avtokredit_ikkilamchi: 'Вторичный рынок',
    },
  },
  {
    label: 'Brendli avtokredit',
    labelRu: 'Брендовый автокредит',
    icon: crownIcon,
    iconColor: '#2a9d8f',
    keys: ['avtokredit_brend_birlamchi', 'avtokredit_brend_ikkilamchi'],
    shortLabels: {
      avtokredit_brend_birlamchi: 'Birlamchi bozor',
      avtokredit_brend_ikkilamchi: 'Ikkilamchi bozor',
    },
    shortLabelsRu: {
      avtokredit_brend_birlamchi: 'Первичный рынок',
      avtokredit_brend_ikkilamchi: 'Вторичный рынок',
    },
  },
  {
    label: 'Elektromobil avtokrediti',
    labelRu: 'Автокредит на электромобиль',
    icon: flashCircleIcon,
    iconColor: '#d4a017',
    keys: ['avtokredit_elektro'],
  },
  {
    label: 'Mikroqarz',
    labelRu: 'Микрозайм',
    icon: walletIcon,
    iconColor: '#7b5ea7',
    keys: ['mikroqarz', 'mikroqarz_onlayn'],
    shortLabels: {
      mikroqarz: 'Oflayn',
      mikroqarz_onlayn: 'Onlayn',
    },
    shortLabelsRu: {
      mikroqarz: 'Офлайн',
      mikroqarz_onlayn: 'Онлайн',
    },
  },
  {
    label: 'Kredit kartalari',
    labelRu: 'Кредитные карты',
    icon: cardIcon,
    iconColor: '#3b6e91',
    keys: ['kredit_karta'],
  },
  {
    label: "Iste'mol krediti",
    labelRu: 'Потребительский кредит',
    icon: moneyIcon,
    iconColor: '#3f8f5f',
    keys: ['istemol_krediti'],
  },
  {
    label: 'Ipoteka krediti',
    labelRu: 'Ипотечный кредит',
    icon: houseIcon,
    iconColor: '#a6485e',
    keys: ['ipoteka_tijorat', 'ipoteka_davlat'],
    shortLabels: {
      ipoteka_tijorat: 'Tijorat',
      ipoteka_davlat: "Davlat mablag'lari",
    },
    shortLabelsRu: {
      ipoteka_tijorat: 'Коммерческий',
      ipoteka_davlat: 'Гос. средства',
    },
  },
]

export function groupLabel(group: CategoryGroup, lang: Lang): string {
  return lang === 'ru' ? group.labelRu : group.label
}

export function groupShortLabel(group: CategoryGroup, key: string, lang: Lang): string | undefined {
  return lang === 'ru' ? group.shortLabelsRu?.[key] : group.shortLabels?.[key]
}

// Sahifa sarlavhasi (h1) uchun: backenddagi to'liq, batafsil category.label
// o'rniga ("Brendli avtokredit — birlamchi (GM, BYD, KIA, ...)" kabi uzun va
// eskirgan brend ro'yxatini o'z ichiga olgan matn) sidebar bilan bir xil,
// qisqa "Guruh nomi — qism nomi" shaklidan foydalaniladi — sidebar allaqachon
// guruh/qism ierarxiyasini ko'rsatib turgani uchun to'liq label sarlavhada
// ortiqcha va "hunuk" ko'rinadi.
export function getCategoryHeading(categoryKey: string, fallbackLabel: string, lang: Lang): string {
  const group = CATEGORY_GROUPS.find((g) => g.keys.includes(categoryKey))
  if (!group) return fallbackLabel
  const label = groupLabel(group, lang)
  const shortLabel = groupShortLabel(group, categoryKey, lang)
  return shortLabel ? `${label} — ${shortLabel}` : label
}
