import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { AuthProvider, useAuth } from './AuthContext'
import * as api from './api'

vi.mock('./api', () => ({
  login: vi.fn(),
  fetchCurrentUser: vi.fn(),
  getToken: vi.fn(),
  setToken: vi.fn(),
  clearToken: vi.fn(),
  setUnauthorizedHandler: vi.fn(),
}))

const mockedApi = vi.mocked(api)

function TestConsumer() {
  const { user, isLoading, login, logout } = useAuth()
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="user">{user ? `${user.username}:${user.role}` : 'none'}</span>
      <button onClick={() => login('admin', 'secret')}>do-login</button>
      <button onClick={logout}>do-logout</button>
    </div>
  )
}

function renderWithAuth() {
  return render(
    <AuthProvider>
      <TestConsumer />
    </AuthProvider>,
  )
}

describe('AuthContext', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('starts with no user and isLoading=false when there is no stored token', async () => {
    mockedApi.getToken.mockReturnValue(null)
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })

  it('restores the session from /auth/me when a token is already stored', async () => {
    mockedApi.getToken.mockReturnValue('stored-token')
    mockedApi.fetchCurrentUser.mockResolvedValue({ username: 'admin', role: 'admin' })
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('admin:admin'))
  })

  it('clears the token and stays logged out when /auth/me fails', async () => {
    mockedApi.getToken.mockReturnValue('stale-token')
    mockedApi.fetchCurrentUser.mockRejectedValue(new Error('unauthorized'))
    renderWithAuth()

    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))
    expect(screen.getByTestId('user')).toHaveTextContent('none')
    expect(mockedApi.clearToken).toHaveBeenCalled()
  })

  it('login stores the token and sets the user', async () => {
    mockedApi.getToken.mockReturnValue(null)
    mockedApi.login.mockResolvedValue({ access_token: 'new-token', username: 'admin', role: 'admin' })
    renderWithAuth()
    await waitFor(() => expect(screen.getByTestId('loading')).toHaveTextContent('false'))

    await userEvent.click(screen.getByText('do-login'))

    expect(mockedApi.setToken).toHaveBeenCalledWith('new-token')
    expect(screen.getByTestId('user')).toHaveTextContent('admin:admin')
  })

  it('logout clears the token and the user', async () => {
    mockedApi.getToken.mockReturnValue('stored-token')
    mockedApi.fetchCurrentUser.mockResolvedValue({ username: 'admin', role: 'admin' })
    renderWithAuth()
    await waitFor(() => expect(screen.getByTestId('user')).toHaveTextContent('admin:admin'))

    await userEvent.click(screen.getByText('do-logout'))

    expect(mockedApi.clearToken).toHaveBeenCalled()
    expect(screen.getByTestId('user')).toHaveTextContent('none')
  })
})
