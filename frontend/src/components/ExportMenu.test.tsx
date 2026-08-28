import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { ExportMenu } from './ExportMenu'
import { LanguageProvider } from '../lib/LanguageContext'
import { downloadFile } from '../lib/api'

vi.mock('../lib/api', async () => {
  const actual = await vi.importActual<typeof import('../lib/api')>('../lib/api')
  return { ...actual, downloadFile: vi.fn() }
})

const mockedDownloadFile = vi.mocked(downloadFile)

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

  it('downloads the current category as an authenticated file when clicked', async () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    await userEvent.click(screen.getByText('Joriy sahifani yuklash'))

    expect(mockedDownloadFile).toHaveBeenCalledWith(
      'http://localhost:8000/export-excel?category=avtokredit&language=uz',
      'avtokredit.xlsx',
    )
  })

  it('downloads all categories as an authenticated file when clicked', async () => {
    renderWithLanguage(<ExportMenu category="avtokredit" />)

    await userEvent.click(screen.getByText("Excel'ga yuklash"))
    await userEvent.click(screen.getByText('Barcha kategoriyalarni yuklash'))

    expect(mockedDownloadFile).toHaveBeenCalledWith(
      'http://localhost:8000/export-excel-all?language=uz',
      'bozor-tahlili-barcha-kategoriyalar.xlsx',
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
