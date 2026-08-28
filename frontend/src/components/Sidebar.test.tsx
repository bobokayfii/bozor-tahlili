import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { Sidebar } from './Sidebar'
import { LanguageProvider } from '../lib/LanguageContext'

const categories = [
  { key: 'avtokredit', label: 'Avtokredit (birlamchi bozor)', schema: 'credit' },
  { key: 'avtokredit_ikkilamchi', label: 'Avtokredit (ikkilamchi bozor)', schema: 'credit' },
  { key: 'kredit_karta', label: 'Kredit kartalari', schema: 'credit' },
]

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('Sidebar', () => {
  it('renders a single button for a standalone category', () => {
    renderWithLanguage(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)
    expect(screen.getByRole('button', { name: 'Kredit kartalari' })).toBeInTheDocument()
  })

  it('renders a collapsed parent button for a grouped category, with its children not in the DOM', () => {
    renderWithLanguage(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: /Avtokredit/ })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Birlamchi bozor' })).not.toBeInTheDocument()
  })

  it('auto-expands the group containing the active category on mount', () => {
    renderWithLanguage(<Sidebar categories={categories} activeCategory="avtokredit_ikkilamchi" onSelect={() => {}} />)

    const child = screen.getByRole('button', { name: 'Ikkilamchi bozor' })
    expect(child).toBeInTheDocument()
    expect(child).toHaveClass('active')
  })

  it('toggles a group open when its parent button is clicked', async () => {
    renderWithLanguage(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)

    const parent = screen.getByRole('button', { name: /Avtokredit/ })
    expect(parent).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('button', { name: 'Birlamchi bozor' })).not.toBeInTheDocument()

    await userEvent.click(parent)

    expect(parent).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('button', { name: 'Birlamchi bozor' })).toBeInTheDocument()
  })

  it('calls onSelect with the child category key when a submenu item is clicked', async () => {
    const onSelect = vi.fn()
    renderWithLanguage(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Ikkilamchi bozor' }))

    expect(onSelect).toHaveBeenCalledWith('avtokredit_ikkilamchi')
  })

  it('calls onSelect with the standalone category key when clicked', async () => {
    const onSelect = vi.fn()
    renderWithLanguage(<Sidebar categories={categories} activeCategory="avtokredit" onSelect={onSelect} />)

    await userEvent.click(screen.getByRole('button', { name: 'Kredit kartalari' }))

    expect(onSelect).toHaveBeenCalledWith('kredit_karta')
  })

  it('renders Russian group and short labels when the stored language is ru', () => {
    window.localStorage.setItem('bozor-tahlili-lang', 'ru')
    renderWithLanguage(<Sidebar categories={categories} activeCategory="avtokredit_ikkilamchi" onSelect={() => {}} />)

    expect(screen.getByRole('button', { name: /Автокредит/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Вторичный рынок' })).toBeInTheDocument()
    window.localStorage.removeItem('bozor-tahlili-lang')
  })

  it('does not render the admin section when isAdmin is false', () => {
    renderWithLanguage(<Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} />)
    expect(screen.queryByText('Boshqaruv')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Foydalanuvchilar' })).not.toBeInTheDocument()
  })

  it('renders the admin section when isAdmin is true', () => {
    renderWithLanguage(
      <Sidebar categories={categories} activeCategory="kredit_karta" onSelect={() => {}} isAdmin />,
    )
    expect(screen.getByText('Boshqaruv')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Foydalanuvchilar' })).toBeInTheDocument()
  })

  it('calls onSelectAdmin when the Foydalanuvchilar button is clicked', async () => {
    const onSelectAdmin = vi.fn()
    renderWithLanguage(
      <Sidebar
        categories={categories}
        activeCategory="kredit_karta"
        onSelect={() => {}}
        isAdmin
        onSelectAdmin={onSelectAdmin}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: 'Foydalanuvchilar' }))

    expect(onSelectAdmin).toHaveBeenCalledOnce()
  })

  it('marks the Foydalanuvchilar button active when isAdminView is true', () => {
    renderWithLanguage(
      <Sidebar categories={categories} activeCategory={null} onSelect={() => {}} isAdmin isAdminView />,
    )
    expect(screen.getByRole('button', { name: 'Foydalanuvchilar' })).toHaveClass('active')
  })
})
