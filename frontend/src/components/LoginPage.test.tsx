import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import type { ReactElement } from 'react'
import { LoginPage } from './LoginPage'
import { LanguageProvider } from '../lib/LanguageContext'
import { useAuth } from '../lib/AuthContext'

vi.mock('../lib/AuthContext', () => ({
  useAuth: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderWithLanguage(ui: ReactElement) {
  return render(<LanguageProvider>{ui}</LanguageProvider>)
}

describe('LoginPage', () => {
  it('calls login with the entered credentials on submit', async () => {
    const mockLogin = vi.fn().mockResolvedValue(undefined)
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: mockLogin, logout: vi.fn() })
    renderWithLanguage(<LoginPage />)

    await userEvent.type(screen.getByLabelText('Login'), 'admin')
    await userEvent.type(screen.getByLabelText('Parol'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }))

    expect(mockLogin).toHaveBeenCalledWith('admin', 'secret123')
  })

  it('shows an error message when login fails', async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error("Login yoki parol noto'g'ri"))
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: mockLogin, logout: vi.fn() })
    renderWithLanguage(<LoginPage />)

    await userEvent.type(screen.getByLabelText('Login'), 'admin')
    await userEvent.type(screen.getByLabelText('Parol'), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }))

    expect(await screen.findByText("Login yoki parol noto'g'ri")).toBeInTheDocument()
  })

  it('shows a distinct message when rate-limited, instead of implying the password is wrong', async () => {
    const mockLogin = vi.fn().mockRejectedValue(new Error('RATE_LIMITED'))
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: mockLogin, logout: vi.fn() })
    renderWithLanguage(<LoginPage />)

    await userEvent.type(screen.getByLabelText('Login'), 'admin')
    await userEvent.type(screen.getByLabelText('Parol'), 'correct-but-rate-limited')
    await userEvent.click(screen.getByRole('button', { name: 'Kirish' }))

    expect(
      await screen.findByText("Juda ko'p urinish. Iltimos, bir necha daqiqadan so'ng qayta urinib ko'ring."),
    ).toBeInTheDocument()
    expect(screen.queryByText("Login yoki parol noto'g'ri")).not.toBeInTheDocument()
  })
})
