import { useEffect, useState } from 'react'
import { fetchUsers } from '../lib/api'
import { useLanguage } from '../lib/LanguageContext'
import { UserFormModal } from './UserFormModal'
import type { AdminUser } from '../lib/types'

interface AdminPanelProps {
  onBack: () => void
}

export function AdminPanel({ onBack }: AdminPanelProps) {
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
      <button type="button" className="admin-panel-back" onClick={onBack}>
        ← {t('adminBackButton')}
      </button>
      <div className="admin-panel-title-row">
        <h1>{t('adminPanelTitle')}</h1>
        <button type="button" className="admin-add-btn" onClick={() => setEditingUser('new')}>
          {t('adminAddUserButton')}
        </button>
      </div>

      {error && <p className="error-state">{error}</p>}

      {!isLoading && (
        <table className="admin-users-table">
          <thead>
            <tr>
              <th>{t('adminUsernameLabel')}</th>
              <th>{t('adminRoleLabel')}</th>
              <th>{t('adminColCreatedAt')}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.username}</td>
                <td>
                  <span className={`admin-role-badge admin-role-badge-${user.role}`}>
                    {user.role === 'admin' ? t('adminRoleAdmin') : t('adminRoleUser')}
                  </span>
                </td>
                <td>{formatCreatedAt(user.created_at)}</td>
                <td>
                  <button type="button" className="admin-edit-btn" onClick={() => setEditingUser(user)}>
                    {t('adminEditButton')}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
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
