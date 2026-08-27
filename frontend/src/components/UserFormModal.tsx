import { useState } from 'react'
import type { FormEvent } from 'react'
import { createUser, updateUser } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import type { AdminUser, UserRole } from '../lib/types'

interface UserFormModalProps {
  user: AdminUser | null
  onClose: () => void
  onSaved: (user: AdminUser) => void
}

export function UserFormModal({ user, onClose, onSaved }: UserFormModalProps) {
  const { t } = useLanguage()
  const isEditing = user !== null
  const [username, setUsername] = useState(user?.username ?? '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>(user?.role ?? 'user')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setIsSubmitting(true)
    setError(null)
    try {
      const saved =
        isEditing && user
          ? await updateUser(user.id, { username, role, ...(password ? { password } : {}) })
          : await createUser({ username, password, role })
      onSaved(saved)
    } catch (err) {
      if (err instanceof Error && err.message === 'USERNAME_TAKEN') {
        setError(t('adminUsernameTaken'))
      } else if (err instanceof Error && err.message === 'SELF_DEMOTE') {
        setError(t('adminSelfDemote'))
      } else {
        setError(t('adminSaveFailed'))
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" role="presentation" onClick={onClose}>
      <div
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="user-form-title"
        onClick={(event) => event.stopPropagation()}
      >
        <h2 id="user-form-title" className="modal-title">
          {isEditing ? t('adminEditUserTitle') : t('adminAddUserTitle')}
        </h2>
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="user-form-username">{t('adminUsernameLabel')}</label>
            <input
              id="user-form-username"
              type="text"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="user-form-password">
              {isEditing ? t('adminPasswordLabelOptional') : t('adminPasswordLabel')}
            </label>
            <input
              id="user-form-password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder={isEditing ? t('adminPasswordPlaceholder') : undefined}
              required={!isEditing}
            />
          </div>
          <div className="form-field">
            <label htmlFor="user-form-role">{t('adminRoleLabel')}</label>
            <select id="user-form-role" value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
              <option value="user">{t('adminRoleUser')}</option>
              <option value="admin">{t('adminRoleAdmin')}</option>
            </select>
          </div>
          {error && <p className="form-error">{error}</p>}
          <div className="modal-actions">
            <button type="button" className="modal-btn modal-btn-secondary" onClick={onClose}>
              {t('refreshConfirmCancel')}
            </button>
            <button type="submit" className="modal-btn modal-btn-primary" disabled={isSubmitting}>
              {t('adminSaveButton')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
