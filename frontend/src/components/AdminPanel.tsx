import { useEffect, useState } from 'react'
import { fetchUsers } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { UserFormModal } from './UserFormModal'
import type { AdminUser } from '../lib/types'

export function AdminPanel() {
  const { lang, t } = useLanguage()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editingUser, setEditingUser] = useState<AdminUser | 'new' | null>(null)

  useEffect(() => {
    loadUsers()
  }, [])

  async function loadUsers() {
    setIsLoading(true)
    try {
      const data = await fetchUsers()
      setUsers(data)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : t('adminLoadFailed'))
    } finally {
      setIsLoading(false)
    }
  }

  function handleSaved(saved: AdminUser) {
    setUsers((prev) => {
      const exists = prev.some((u) => u.id === saved.id)
      return exists ? prev.map((u) => (u.id === saved.id ? saved : u)) : [...prev, saved]
    })
    setEditingUser(null)
  }

  function formatCreatedAt(iso: string): string {
    const locale = lang === 'ru' ? 'ru-RU' : 'uz-UZ'
    return new Date(iso).toLocaleDateString(locale, { day: '2-digit', month: '2-digit', year: 'numeric' })
  }

  return (
    <div className="admin-panel">
      <div className="page-head">
        <div>
          <h1>{t('adminPanelTitle')}</h1>
          <p className="page-subtitle">{t('adminPanelSubtitle')}</p>
        </div>
        <button type="button" className="admin-add-btn" onClick={() => setEditingUser('new')}>
          {t('adminAddUserButton')}
        </button>
      </div>

      {error && <p className="error-state">{error}</p>}

      {!isLoading && (
        <div className="admin-users-board rate-board">
          <div className="rate-board-head">
            <span>{t('tableRank')}</span>
            <span>{t('adminUsernameLabel')}</span>
            <span>{t('adminRoleLabel')}</span>
            <span>{t('adminColCreatedAt')}</span>
            <span />
          </div>
          {users.map((user, index) => (
            <div className="rate-row" key={user.id}>
              <span className="rate-rank">{String(index + 1).padStart(2, '0')}</span>
              <span className="rate-bank">
                <span className="admin-user-avatar" aria-hidden="true">
                  {user.username.slice(0, 1).toUpperCase()}
                </span>
                <span className="rate-bank-name">{user.username}</span>
              </span>
              <span>
                <span className={`admin-role-badge admin-role-badge-${user.role}`}>
                  {user.role === 'admin' ? t('adminRoleAdmin') : t('adminRoleUser')}
                </span>
              </span>
              <span className="rate-term">{formatCreatedAt(user.created_at)}</span>
              <span>
                <button type="button" className="admin-edit-btn" onClick={() => setEditingUser(user)}>
                  {t('adminEditButton')}
                </button>
              </span>
            </div>
          ))}
        </div>
      )}

      {editingUser && (
        <UserFormModal
          user={editingUser === 'new' ? null : editingUser}
          onClose={() => setEditingUser(null)}
          onSaved={handleSaved}
        />
      )}
    </div>
  )
}
