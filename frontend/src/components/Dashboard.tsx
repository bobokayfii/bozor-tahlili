import { useEffect, useState } from 'react'
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { CategoryPage } from './CategoryPage'
import { AdminPanel } from './AdminPanel'
import { ExportMenu } from './ExportMenu'
import { RefreshDataButton } from './RefreshDataButton'
import { LanguageDropdown } from './LanguageDropdown'
import { LogoutIcon } from './icons'
import { fetchCategories } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { useAuth } from '../lib/AuthContext'
import type { AuthUser, Category } from '../lib/types'
import logoIcon from '../assets/logo-icon.png'

interface DashboardProps {
  user: AuthUser
}

export function Dashboard({ user }: DashboardProps) {
  const { t } = useLanguage()
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [categories, setCategories] = useState<Category[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchCategories()
      .then((data) => setCategories(data))
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Kategoriyalarni yuklab bo'lmadi")
      })
  }, [])

  const isAdminView = location.pathname === '/admin'
  const activeCategoryKey = isAdminView ? null : location.pathname.slice(1) || null

  function handleSelectCategory(categoryKey: string) {
    navigate(`/${categoryKey}`)
  }

  function handleSelectAdmin() {
    navigate('/admin')
  }

  return (
    <div className="app-shell">
      <header className="app-topbar">
        <div className="app-topbar-brand">
          <img src={logoIcon} alt="" className="app-topbar-logo-icon" />
          <span className="app-topbar-wordmark">{t('brandName')}</span>
        </div>
        <div className="app-topbar-actions">
          {!isAdminView && (
            <>
              {user.role === 'admin' && <RefreshDataButton />}
              <ExportMenu category={activeCategoryKey} />
            </>
          )}
          <LanguageDropdown />
          <div className="app-topbar-user">
            <span className="app-topbar-username">{user.username}</span>
            <button type="button" className="app-topbar-logout-btn" onClick={logout} aria-label={t('logoutButton')}>
              <LogoutIcon />
            </button>
          </div>
        </div>
      </header>
      <div className="app-body">
        <Sidebar
          categories={categories}
          activeCategory={activeCategoryKey}
          onSelect={handleSelectCategory}
          isAdmin={user.role === 'admin'}
          isAdminView={isAdminView}
          onSelectAdmin={handleSelectAdmin}
        />
        <main className="main-content">
          {error && <p className="error-state">{error}</p>}
          <Routes>
            <Route
              index
              element={categories.length > 0 ? <Navigate to={`/${categories[0].key}`} replace /> : null}
            />
            <Route
              path="admin"
              element={user.role === 'admin' ? <AdminPanel /> : <Navigate to="/" replace />}
            />
            <Route path=":categoryKey" element={<CategoryPage categories={categories} />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}
