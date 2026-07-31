import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { CompareModal } from './CompareModal'
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

const nbu: Product = {
  ...sqb,
  bank: 'NBU',
  product_name: 'NBU Avtokredit',
  rate_min: 20.9,
  rate_max: 23.9,
  amount_max_som: 900_000_000,
  grace_period_months: 0,
}

describe('CompareModal', () => {
  it('renders one column per selected product with bank and product name', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    expect(screen.getByText('SQB')).toBeInTheDocument()
    expect(screen.getByText('NBU')).toBeInTheDocument()
    expect(screen.getByText('SQB Avtokredit')).toBeInTheDocument()
    expect(screen.getByText('NBU Avtokredit')).toBeInTheDocument()
  })

  it('highlights the cheapest rate cell as best', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    const nbuRateCell = screen.getByText('20.9% – 23.9%')
    const sqbRateCell = screen.getByText('24.9% – 27.9%')
    expect(nbuRateCell).toHaveClass('compare-cell-best')
    expect(sqbRateCell).not.toHaveClass('compare-cell-best')
  })

  it('highlights the highest amount cell as best', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    expect(screen.getByText("900 mln so'm")).toHaveClass('compare-cell-best')
    expect(screen.getByText("800 mln so'm")).not.toHaveClass('compare-cell-best')
  })

  it('does not highlight the term row since it is a neutral attribute', () => {
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={vi.fn()} />)
    const termCells = screen.getAllByText('12–60 oy')
    expect(termCells).toHaveLength(2)
    termCells.forEach((cell) => expect(cell).not.toHaveClass('compare-cell-best'))
  })

  it('calls onRemove with the compare key when a column remove button is clicked', async () => {
    const user = userEvent.setup()
    const onRemove = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={vi.fn()} onRemove={onRemove} />)
    // Index 0 is the modal's own close button ("Yopish"); the column remove
    // buttons for SQB then NBU follow it in DOM order.
    const removeButtons = screen.getAllByRole('button', { name: 'Yopish' })
    await user.click(removeButtons[1])
    expect(onRemove).toHaveBeenCalledWith('SQB::SQB Avtokredit')
  })

  it('calls onClose when Escape is pressed', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={onClose} onRemove={vi.fn()} />)
    await user.keyboard('{Escape}')
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when the overlay is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()
    renderWithLanguage(<CompareModal products={[sqb, nbu]} onClose={onClose} onRemove={vi.fn()} />)
    // Decorative logos (alt="") also carry an implicit "presentation" role,
    // so we locate the overlay via the dialog's parent rather than by role.
    const overlay = screen.getByRole('dialog').parentElement as HTMLElement
    await user.click(overlay)
    expect(onClose).toHaveBeenCalled()
  })
})
