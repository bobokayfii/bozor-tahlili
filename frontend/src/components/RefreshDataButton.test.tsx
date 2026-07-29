import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import type { ReactElement } from 'react'
import { RefreshDataButton } from './RefreshDataButton'
import { triggerScrapeRefresh } from '../lib/api'
import { LanguageProvider } from '../lib/LanguageContext'

vi.mock('../lib/api', () => ({
  triggerScrapeRefresh: vi.fn(),
}))

const mockedTriggerScrapeRefresh = vi.mocked(triggerScrapeRefresh)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('RefreshDataButton', () => {
  beforeEach(() => {
    mockedTriggerScrapeRefresh.mockReset()
  })

  it('does not call the API until the confirm dialog is accepted', async () => {
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))

    expect(screen.getByText("Ma'lumotlarni qayta yig'ish")).toBeInTheDocument()
    expect(mockedTriggerScrapeRefresh).not.toHaveBeenCalled()
  })

  it('closes the dialog without calling the API when cancelled', async () => {
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))
    await userEvent.click(screen.getByText('Bekor qilish'))

    expect(screen.queryByText("Ma'lumotlarni qayta yig'ish")).not.toBeInTheDocument()
    expect(mockedTriggerScrapeRefresh).not.toHaveBeenCalled()
  })

  it('calls the API and shows the success message when confirmed', async () => {
    mockedTriggerScrapeRefresh.mockResolvedValue('started')
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))
    await userEvent.click(screen.getByText('Ha, boshlash'))

    expect(mockedTriggerScrapeRefresh).toHaveBeenCalledOnce()
    expect(await screen.findByText(/taxminan 5 daqiqadan/)).toBeInTheDocument()
  })

  it('shows the already-running message (not an error) when the API returns that status', async () => {
    mockedTriggerScrapeRefresh.mockResolvedValue('already_running')
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))
    await userEvent.click(screen.getByText('Ha, boshlash'))

    const message = await screen.findByText(/allaqachon ishlamoqda/)
    expect(message.closest('.refresh-status')).toHaveClass('refresh-status-warning')
  })

  it('shows an error message when the API call fails outright', async () => {
    mockedTriggerScrapeRefresh.mockRejectedValue(new Error('network down'))
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))
    await userEvent.click(screen.getByText('Ha, boshlash'))

    const message = await screen.findByText(/Yangilashni boshlab bo'lmadi/)
    expect(message.closest('.refresh-status')).toHaveClass('refresh-status-error')
  })

  it('dismisses the status message when its close button is clicked', async () => {
    mockedTriggerScrapeRefresh.mockResolvedValue('started')
    renderWithLanguage(<RefreshDataButton />)

    await userEvent.click(screen.getByText("Ma'lumotlarni yangilash"))
    await userEvent.click(screen.getByText('Ha, boshlash'))
    await screen.findByText(/taxminan 5 daqiqadan/)

    await userEvent.click(screen.getByLabelText('Yopish'))

    expect(screen.queryByText(/taxminan 5 daqiqadan/)).not.toBeInTheDocument()
  })
})
