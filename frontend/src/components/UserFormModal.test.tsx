import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { UserFormModal } from './UserFormModal'
import { LanguageProvider } from '../lib/LanguageContext'
import { createUser, updateUser } from '../lib/api'

vi.mock('../lib/api', () => ({
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

const mockedCreateUser = vi.mocked(createUser)
const mockedUpdateUser = vi.mocked(updateUser)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('UserFormModal', () => {
  it('creates a new user with the entered fields', async () => {
    const savedUser = { id: 2, username: 'jane', role: 'user' as const, created_at: '2026-01-01T00:00:00Z' }
    mockedCreateUser.mockResolvedValue(savedUser)
    const onSaved = vi.fn()
    renderWithLanguage(<UserFormModal user={null} onClose={vi.fn()} onSaved={onSaved} />)

    await userEvent.type(screen.getByLabelText('Login'), 'jane')
    await userEvent.type(screen.getByLabelText('Parol'), 'jane-password')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(mockedCreateUser).toHaveBeenCalledWith({ username: 'jane', password: 'jane-password', role: 'user' })
    expect(onSaved).toHaveBeenCalledWith(savedUser)
  })

  it('updates an existing user, omitting the password when left blank', async () => {
    const existingUser = { id: 5, username: 'bob', role: 'user' as const, created_at: '2026-01-01T00:00:00Z' }
    const savedUser = { ...existingUser, role: 'admin' as const }
    mockedUpdateUser.mockResolvedValue(savedUser)
    const onSaved = vi.fn()
    renderWithLanguage(<UserFormModal user={existingUser} onClose={vi.fn()} onSaved={onSaved} />)

    await userEvent.selectOptions(screen.getByLabelText('Rol'), 'admin')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(mockedUpdateUser).toHaveBeenCalledWith(5, { username: 'bob', role: 'admin' })
    expect(onSaved).toHaveBeenCalledWith(savedUser)
  })

  it('shows a "username taken" error when the API rejects with a conflict', async () => {
    mockedCreateUser.mockRejectedValue(new Error('USERNAME_TAKEN'))
    renderWithLanguage(<UserFormModal user={null} onClose={vi.fn()} onSaved={vi.fn()} />)

    await userEvent.type(screen.getByLabelText('Login'), 'jane')
    await userEvent.type(screen.getByLabelText('Parol'), 'pw')
    await userEvent.click(screen.getByRole('button', { name: 'Saqlash' }))

    expect(await screen.findByText('Bu login band')).toBeInTheDocument()
  })

  it('closes when the overlay is clicked', async () => {
    const onClose = vi.fn()
    renderWithLanguage(<UserFormModal user={null} onClose={onClose} onSaved={vi.fn()} />)

    await userEvent.click(screen.getByRole('dialog').parentElement as HTMLElement)

    expect(onClose).toHaveBeenCalled()
  })

  it('closes when the Escape key is pressed', async () => {
    const onClose = vi.fn()
    renderWithLanguage(<UserFormModal user={null} onClose={onClose} onSaved={vi.fn()} />)

    await userEvent.keyboard('{Escape}')

    expect(onClose).toHaveBeenCalled()
  })
})
