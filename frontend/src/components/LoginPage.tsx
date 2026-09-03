import { useState } from 'react'
import type { FormEvent } from 'react'
import { useAuth } from '../lib/AuthContext'
import { useLanguage } from '../lib/LanguageContext'
import { LanguageDropdown } from './LanguageDropdown'
import { PasswordInput } from './PasswordInput'
import sqbMark from '../assets/bank-logos/sqb2.svg'

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
    } catch (err) {
      setError(err instanceof Error && err.message === 'RATE_LIMITED' ? t('authRateLimited') : t('authError'))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-page">
      <header className="auth-topbar">
        <span className="auth-topbar-brand">{t('brandName')}</span>
        <LanguageDropdown />
      </header>
      <main className="auth-center">
        <div className="auth-card">
          <img src={sqbMark} alt="SQB" className="auth-mark" />
          <div className="auth-rule" aria-hidden="true" />
          <h1>{t('authTitle')}</h1>
          <form onSubmit={handleSubmit} noValidate>
            <div className="form-field">
              <label htmlFor="login-username">{t('authUsernameLabel')}</label>
              <input
                id="login-username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                // Deliberate: the first field on a dedicated, single-purpose
                // login page - not mid-page or competing with other content,
                // which is what the rule is meant to guard against.
                // eslint-disable-next-line jsx-a11y/no-autofocus
                autoFocus
                required
              />
            </div>
            <div className="form-field">
              <label htmlFor="login-password">{t('authPasswordLabel')}</label>
              <PasswordInput
                id="login-password"
                value={password}
                onChange={setPassword}
                autoComplete="current-password"
                required
              />
            </div>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="auth-submit" disabled={isSubmitting}>
              {isSubmitting ? <span className="auth-spinner" aria-hidden="true" /> : t('authSubmitButton')}
            </button>
          </form>
          <p className="auth-footer">{t('sidebarFooter')}</p>
        </div>
      </main>
    </div>
  )
}
