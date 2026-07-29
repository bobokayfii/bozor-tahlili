import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect } from 'vitest'
import type { ReactElement } from 'react'
import { ExportMenu } from './ExportMenu'
import { LanguageProvider } from '../lib/LanguageContext'

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('ExportMenu', () => {
  it('renders nothing when there is no active category', () => {
    renderWithLanguage(<ExportMenu category={null} />)
    expect(screen.queryByText("Excel'ga yuklash")).not.toBeInTheDocument()
  })

  it('shows the toggle button but keeps the menu closed until clicked', () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)
    expect(screen.getByText("Excel'ga yuklash")).toBeInTheDocument()
    expect(screen.queryByText('Joriy sahifani yuklash')).not.toBeInTheDocument()
  })

  it('opens the menu with both options, linking to the correct URLs', async () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)

    await userEvent.click(screen.getByText("Excel'ga yuklash"))

    const currentPageLink = screen.getByText('Joriy sahifani yuklash')
    const allCategoriesLink = screen.getByText('Barcha kategoriyalarni yuklash')
    expect(currentPageLink).toBeInTheDocument()
    expect(allCategoriesLink).toBeInTheDocument()
    expect(currentPageLink.closest('a')).toHaveAttribute(
      'href',
      'http://localhost:8000/export-excel?category=avtokredit&language=uz',
    )
    expect(allCategoriesLink.closest('a')).toHaveAttribute(
      'href',
      'http://localhost:8000/export-excel-all?language=uz',
    )
  })

  it('closes the menu when a click lands outside it', async () => {
    renderWithLanguage(
      <div>
        <ExportMenu category="avtokredit" />
        <button type="button">outside</button>
      </div>,
    )

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    expect(screen.getByText('Joriy sahifani yuklash')).toBeInTheDocument()

    await userEvent.click(screen.getByText('outside'))
    expect(screen.queryByText('Joriy sahifani yuklash')).not.toBeInTheDocument()
  })
})
