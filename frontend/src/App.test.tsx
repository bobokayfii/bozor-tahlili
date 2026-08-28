import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { App } from './App'
import { LanguageProvider } from './lib/LanguageContext'
import { useAuth } from './lib/AuthContext'

vi.mock('./lib/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('./lib/api', () => ({
  fetchCategories: vi.fn().mockResolvedValue([]),
  fetchProducts: vi.fn().mockResolvedValue([]),
  fetchUnavailableBanks: vi.fn().mockResolvedValue([]),
}))

const mockedUseAuth = vi.mocked(useAuth)

function renderApp(initialPath = '/') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <LanguageProvider>
        <App />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe('App auth gating', () => {
  it('shows a loading state while the session is being restored', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: true, login: vi.fn(), logout: vi.fn() })
    renderApp()
    expect(screen.getByText('Yuklanmoqda')).toBeInTheDocument()
  })

  it('shows the login page when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
    renderApp()
    expect(screen.getByRole('button', { name: 'Kirish' })).toBeInTheDocument()
  })

  it('renders the dashboard shell instead of the login page once authenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'jane', role: 'user' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp()
    expect(screen.queryByRole('button', { name: 'Kirish' })).not.toBeInTheDocument()
    expect(screen.getByText('jane')).toBeInTheDocument()
  })

  it('redirects away from /login back to the dashboard when already authenticated', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'jane', role: 'user' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp('/login')
    expect(screen.queryByRole('button', { name: 'Kirish' })).not.toBeInTheDocument()
    expect(screen.getByText('jane')).toBeInTheDocument()
  })
})
