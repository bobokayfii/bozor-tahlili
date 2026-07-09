import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { Sidebar } from './Sidebar'

const categories = [
  { key: 'avtokredit', label: 'Avtokredit', schema: 'credit' },
  { key: 'mikroqarz', label: 'Mikroqarz', schema: 'credit' },
]

describe('Sidebar', () => {
  it('renders a button for each category', () => {
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: 'Avtokredit' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mikroqarz' })).toBeInTheDocument()
  })

  it('marks the active category button', () => {
    render(<Sidebar categories={categories} activeCategory="mikroqarz" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: 'Mikroqarz' })).toHaveClass('active')
    expect(screen.getByRole('button', { name: 'Avtokredit' })).not.toHaveClass('active')
  })

  it('calls onSelect with the clicked category key', async () => {
    const onSelect = vi.fn()
    render(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Mikroqarz' }))

    expect(onSelect).toHaveBeenCalledWith('mikroqarz')
  })
})
