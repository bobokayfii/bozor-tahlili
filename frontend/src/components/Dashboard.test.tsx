import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { Dashboard } from './Dashboard'
import { LanguageProvider } from '../lib/LanguageContext'
import { useAuth } from '../lib/AuthContext'
import { fetchCategories, fetchUsers } from '../lib/api'

vi.mock('../lib/AuthContext', () => ({
  useAuth: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  fetchCategories: vi.fn(),
  fetchProducts: vi.fn().mockResolvedValue([]),
  fetchUnavailableBanks: vi.fn().mockResolvedValue([]),
  fetchUsers: vi.fn(),
  createUser: vi.fn(),
  updateUser: vi.fn(),
}))

const mockedUseAuth = vi.mocked(useAuth)
const mockedFetchCategories = vi.mocked(fetchCategories)
const mockedFetchUsers = vi.mocked(fetchUsers)

const categories = [
  { key: 'avtokredit', label: 'Avtokredit', schema: 'credit' },
  { key: 'mikroqarz', label: 'Mikroqarz', schema: 'credit' },
]

function renderDashboard(role: 'admin' | 'user', initialPath = '/') {
  mockedUseAuth.mockReturnValue({ user: null, isLoading: false, login: vi.fn(), logout: vi.fn() })
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <LanguageProvider>
        <Dashboard user={{ username: role === 'admin' ? 'admin' : 'jane', role }} />
      </LanguageProvider>
    </MemoryRouter>,
  )
}

describe('Dashboard', () => {
  it('redirects to the first category at the root path once categories load', async () => {
    mockedFetchCategories.mockResolvedValue(categories)
    renderDashboard('user', '/')
    expect(await screen.findByText('Avtokredit')).toBeInTheDocument()
  })

  it('redirects a non-admin user away from /admin back to the first category', async () => {
    mockedFetchCategories.mockResolvedValue(categories)
    renderDashboard('user', '/admin')

    expect(await screen.findByText('Avtokredit')).toBeInTheDocument()
    expect(screen.queryByText('Foydalanuvchilarni boshqarish')).not.toBeInTheDocument()
  })

  it('shows the Foydalanuvchilar sidebar link only for admins and navigates via it', async () => {
    mockedFetchCategories.mockResolvedValue(categories)
    mockedFetchUsers.mockResolvedValue([])
    renderDashboard('admin')
    await screen.findByText('Avtokredit')

    await userEvent.click(screen.getByRole('button', { name: 'Foydalanuvchilar' }))

    expect(await screen.findByText('Foydalanuvchilarni boshqarish')).toBeInTheDocument()
  })
})
