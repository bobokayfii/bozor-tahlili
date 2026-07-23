import nbuLogo from '../assets/bank-logos/nbu.svg'
import sqbLogo from '../assets/bank-logos/sqb.svg'
import hamkorbankLogo from '../assets/bank-logos/hamkorbank.svg'
import agrobankLogo from '../assets/bank-logos/agrobank.svg'
import ipotekaBankLogo from '../assets/bank-logos/ipotekabank.svg'
import ipakYuliLogo from '../assets/bank-logos/ipakyuli.svg'
import kapitalbankLogo from '../assets/bank-logos/kapitalbank.svg'
import mikrokreditbankLogo from '../assets/bank-logos/mikrokreditbank.svg'
import tbcLogo from '../assets/bank-logos/tbc.svg'
import tengeBankLogo from '../assets/bank-logos/tengebank.svg'
import turonbankLogo from '../assets/bank-logos/turonbank.svg'
import xalqBankiLogo from '../assets/bank-logos/xalqbank.svg'
import asakabankLogo from '../assets/bank-logos/asakabank.svg'
import infinbankLogo from '../assets/bank-logos/infinbank.svg'

const BANK_LOGOS: Record<string, string> = {
  nbu: nbuLogo,
  sqb: sqbLogo,
  hamkorbank: hamkorbankLogo,
  agrobank: agrobankLogo,
  'ipoteka bank': ipotekaBankLogo,
  "ipak yo'li bank": ipakYuliLogo,
  kapitalbank: kapitalbankLogo,
  mikrokreditbank: mikrokreditbankLogo,
  'tbc bank': tbcLogo,
  'tenge bank': tengeBankLogo,
  turonbank: turonbankLogo,
  'xalq banki': xalqBankiLogo,
  asakabank: asakabankLogo,
  infinbank: infinbankLogo,
}

export function getBankLogo(bank: string): string | undefined {
  return BANK_LOGOS[bank.trim().toLowerCase()]
}
