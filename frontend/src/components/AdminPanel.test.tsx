import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { AdminPanel } from './AdminPanel'
import { LanguageProvider } from '../lib/LanguageContext'
import { fetchUsers } from '../lib/api'

vi.mock('../lib/api', () => ({
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

const mockedFetchUsers = vi.mocked(fetchUsers)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('AdminPanel', () => {
  it('lists the users returned by the API', async () => {
    mockedFetchUsers.mockResolvedValue([
      { id: 1, username: 'admin1', role: 'admin', created_at: '2026-01-01T00:00:00Z' },
      { id: 2, username: 'jane', role: 'user', created_at: '2026-02-01T00:00:00Z' },
    ])
    renderWithLanguage(<AdminPanel />)

    expect(await screen.findByText('admin1')).toBeInTheDocument()
    expect(screen.getByText('jane')).toBeInTheDocument()
  })

  it('opens the add-user modal when the add button is clicked', async () => {
    mockedFetchUsers.mockResolvedValue([])
    renderWithLanguage(<AdminPanel />)

    await userEvent.click(await screen.findByText("Yangi user qo'shish"))

    expect(screen.getByText('Yangi user')).toBeInTheDocument()
  })

  it('opens the edit modal pre-filled for an existing user', async () => {
    mockedFetchUsers.mockResolvedValue([
      { id: 3, username: 'bob', role: 'user', created_at: '2026-01-01T00:00:00Z' },
    ])
    renderWithLanguage(<AdminPanel />)

    await userEvent.click(await screen.findByText('Tahrirlash'))

    expect(screen.getByText('Userni tahrirlash')).toBeInTheDocument()
    expect(screen.getByLabelText('Login')).toHaveValue('bob')
  })
})
