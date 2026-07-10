import nbuLogo from '../bank_logo/svg.svg'
import sqbLogo from '../bank_logo/svg (1).svg'
import hamkorbankLogo from '../bank_logo/svg (2).svg'
import agrobankLogo from '../bank_logo/svg (4).svg'
import ipotekaBankLogo from '../bank_logo/svg (5).svg'

const BANK_LOGOS: Record<string, string> = {
  nbu: nbuLogo,
  sqb: sqbLogo,
  hamkorbank: hamkorbankLogo,
  agrobank: agrobankLogo,
  'ipoteka bank': ipotekaBankLogo,
}

export function getBankLogo(bank: string): string | undefined {
  return BANK_LOGOS[bank.trim().toLowerCase()]
}
