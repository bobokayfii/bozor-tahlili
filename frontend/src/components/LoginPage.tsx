import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../lib/AuthContext'
import { useLanguage } from '../lib/LanguageContext'
import { BANK_LOGO_LIST } from '../lib/bankLogos'
import logoIcon from '../assets/logo-icon.png'

export function LoginPage() {
  const { login } = useAuth()
  const { t } = useLanguage()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      await login(username, password)
    } catch {
      setError(t('authError'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-showcase">
        <div className="auth-showcase-brand">
          <img src={logoIcon} alt="" className="auth-showcase-logo-icon" />
          <span className="auth-showcase-wordmark">{t('brandName')}</span>
        </div>
        <p className="auth-showcase-tagline">{t('authTagline')}</p>
        <div className="auth-showcase-logos">
          {BANK_LOGO_LIST.map(({ key, src }, index) => (
            <div key={key} className="auth-showcase-logo-chip" style={{ animationDelay: `${index * 40}ms` }}>
              <img src={src} alt="" />
            </div>
          ))}
        </div>
      </div>
      <div className="auth-form-panel">
        <div className="auth-form-card">
          <h1>{t('authTitle')}</h1>
          <p className="auth-form-subtitle">{t('authSubtitle')}</p>
          <form onSubmit={handleSubmit}>
            <div className="form-field">
              <label htmlFor="login-username">{t('authUsernameLabel')}</label>
              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="login-password">{t('authPasswordLabel')}</label>
              <input
                id="login-password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            {error && <p className="form-error">{error}</p>}
            <button type="submit" className="auth-form-submit" disabled={isSubmitting}>
              {t('authSubmitButton')}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
