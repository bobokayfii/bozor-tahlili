import { render, screen } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
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

function renderApp() {
  return render(
    <LanguageProvider>
      <App />
    </LanguageProvider>,
  )
}

describe('App auth gating', () => {
  it('shows the login page when there is no authenticated user', () => {
    mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
    renderApp()
    expect(screen.getByRole('button', { name: 'Kirish' })).toBeInTheDocument()
  })

  it('does not show the Dashboard button for a regular user', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'jane', role: 'user' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp()
    expect(screen.queryByText('Dashboard')).not.toBeInTheDocument()
  })

  it('shows the Dashboard button for an admin user', () => {
    mockedUseAuth.mockReturnValue({
      user: { username: 'admin', role: 'admin' },
      isLoading: false,
      login: vi.fn(),
      logout: vi.fn(),
    })
    renderApp()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
  })
})
