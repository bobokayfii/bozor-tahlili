import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Sidebar } from './Sidebar'

const categories = [
  { key: 'avtokredit', label: 'Avtokredit (birlamchi bozor)', schema: 'credit' },
  { key: 'avtokredit_ikkilamchi', label: 'Avtokredit (ikkilamchi bozor)', schema: 'credit' },
  { key: 'kredit_karta', label: 'Kredit kartalari', schema: 'credit' },
]

describe('Sidebar', () => {
  it('renders a single button for a standalone category', () => {
    render(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)
    expect(screen.getByRole('button', { name: 'Kredit kartalari' })).toBeInTheDocument()
  })

  it('renders a collapsed parent button for a grouped category, with its children not in the DOM', () => {
    render(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: /Avtokredit/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Birlamchi bozor' })).not.toBeInTheDocument()
  })

  it('auto-expands the group containing the active category on mount', () => {
    render(<Sidebar categories={categories} activeCategory="avtokredit_ikkilamchi" onSelect={() => {}} />)

    const child = screen.getByRole('button', { name: 'Ikkilamchi bozor' })
    expect(child).toBeInTheDocument()
    expect(child).toHaveClass('active')
  })

  it('toggles a group open when its parent button is clicked', async () => {
    render(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)

    const parent = screen.getByRole('button', { name: /Avtokredit/ })
    expect(parent).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('button', { name: 'Birlamchi bozor' })).not.toBeInTheDocument()

    await userEvent.click(parent)

    expect(parent).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Birlamchi bozor' })).toBeInTheDocument()
  })

  it('calls onSelect with the child category key when a submenu item is clicked', async () => {
    const onSelect = vi.fn()
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Ikkilamchi bozor' }))

    expect(onSelect).toHaveBeenCalledWith('avtokredit_ikkilamchi')
  })

  it('calls onSelect with the standalone category key when clicked', async () => {
    const onSelect = vi.fn()
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Kredit kartalari' }))

    expect(onSelect).toHaveBeenCalledWith('kredit_karta')
  })
})
