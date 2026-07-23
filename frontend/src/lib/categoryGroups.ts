import carIcon from '../assets/icons/car.png'
import crownIcon from '../assets/icons/crown.png'
import flashCircleIcon from '../assets/icons/flash-circle.png'
import walletIcon from '../assets/icons/wallet.png'
import cardIcon from '../assets/icons/card.png'
import moneyIcon from '../assets/icons/money.png'
import houseIcon from '../assets/icons/house.png'

export interface CategoryGroup {
  label: string
  icon: string
  iconColor: string
  keys: string[]
  shortLabels?: Record<string, string>
}

export const CATEGORY_GROUPS: CategoryGroup[] = [
  {
    label: 'Avtokredit',
    icon: carIcon,
    iconColor: '#c2703a',
    keys: ['avtokredit', 'avtokredit_ikkilamchi'],
    shortLabels: {
      avtokredit: 'Birlamchi bozor',
      avtokredit_ikkilamchi: 'Ikkilamchi bozor',
    },
  },
  {
    label: 'Brendli avtokredit',
    icon: crownIcon,
    iconColor: '#2a9d8f',
    keys: ['avtokredit_brend_birlamchi', 'avtokredit_brend_ikkilamchi'],
    shortLabels: {
      avtokredit_brend_birlamchi: 'Birlamchi bozor',
      avtokredit_brend_ikkilamchi: 'Ikkilamchi bozor',
    },
  },
  {
    label: 'Elektromobil avtokrediti',
    icon: flashCircleIcon,
    iconColor: '#d4a017',
    keys: ['avtokredit_elektro'],
  },
  {
    label: 'Mikroqarz',
    icon: walletIcon,
    iconColor: '#7b5ea7',
    keys: ['mikroqarz', 'mikroqarz_onlayn'],
    shortLabels: {
      mikroqarz: 'Oflayn',
      mikroqarz_onlayn: 'Onlayn',
    },
  },
  {
    label: 'Kredit kartalari',
    icon: cardIcon,
    iconColor: '#3b6e91',
    keys: ['kredit_karta'],
  },
  {
    label: "Iste'mol krediti",
    icon: moneyIcon,
    iconColor: '#3f8f5f',
    keys: ['istemol_krediti'],
  },
  {
    label: 'Ipoteka krediti',
    icon: houseIcon,
    iconColor: '#a6485e',
    keys: ['ipoteka_tijorat', 'ipoteka_davlat'],
    shortLabels: {
      ipoteka_tijorat: 'Tijorat',
      ipoteka_davlat: "Davlat mablag'lari",
    },
  },
]
