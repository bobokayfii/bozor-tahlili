import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { CompareBar } from './CompareBar'
import { LanguageProvider } from '../lib/LanguageContext'
import type { Product } from '../lib/types'

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

const sqb: Product = {
  bank: 'SQB',
  category: 'avtokredit',
  product_name: 'SQB Avtokredit',
  rate_min: 24.9,
  rate_max: 27.9,
  term_min_months: 12,
  term_max_months: 60,
  amount_max_som: 800_000_000,
  requires_collateral: true,
  down_payment_pct: 30,
  grace_period_months: 3,
  payment_method: 'Annuitet',
  special_terms: null,
  scraped_at: '2026-07-08T10:00:00Z',
}

const nbu: Product = { ...sqb, bank: 'NBU', product_name: 'NBU Avtokredit' }

describe('CompareBar', () => {
  it('renders nothing when there are no selected products', () => {
    const { container } = renderWithLanguage(
      <CompareBar products={[]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders one chip per selected product', () => {
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('NBU')).toBeInTheDocument()
  })

  it('calls onRemove with the compare key when a chip is removed', async () => {
    const user = userEvent.setup()
    const onRemove = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb]} onRemove={onRemove} onOpen={vi.fn()} onClear={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: 'Yopish' }))
    expect(onRemove).toHaveBeenCalledWith('SQB::SQB Avtokredit')
  })

  it('calls onOpen when the compare button is clicked', async () => {
    const user = userEvent.setup()
    const onOpen = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={onOpen} onClear={vi.fn()} />)
    await user.click(screen.getByRole('button', { name: /Solishtirish/ }))
    expect(onOpen).toHaveBeenCalled()
  })

  it('calls onClear when the clear button is clicked', async () => {
    const user = userEvent.setup()
    const onClear = vi.fn()
    renderWithLanguage(<CompareBar products={[sqb, nbu]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={onClear} />)
    await user.click(screen.getByRole('button', { name: 'Bekor qilish' }))
    expect(onClear).toHaveBeenCalled()
  })

  it('disables the compare button when only one product is selected', () => {
    renderWithLanguage(<CompareBar products={[sqb]} onRemove={vi.fn()} onOpen={vi.fn()} onClear={vi.fn()} />)
    expect(screen.getByRole('button', { name: /Solishtirish/ })).toBeDisabled()
  })
})
