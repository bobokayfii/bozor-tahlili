import { Navigate, Route, Routes } from 'react-router-dom'
import { LoginPage } from './components/LoginPage'
import { Dashboard } from './components/Dashboard'
import { useAuth } from './lib/AuthContext'
import { useLanguage } from './lib/LanguageContext'

export function App() {
  const { user, isLoading } = useAuth()
  const { t } = useLanguage()

  if (isLoading) {
    return <div className="auth-loading">{t('loadingLabel')}</div>
  }

  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/*" element={user ? <Dashboard user={user} /> : <Navigate to="/login" replace />} />
    </Routes>
  )
}
