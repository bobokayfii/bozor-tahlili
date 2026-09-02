import { createContext, useContext, useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import {
  clearToken,
  fetchCurrentUser,
  getToken,
  login as loginRequest,
  setToken,
  setUnauthorizedHandler,
} from './api'
import type { AuthUser } from './types'

interface AuthContextValue {
  user: AuthUser | null
  isLoading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  // No stored token means there's nothing to restore - known synchronously
  // at mount, so it's the initial value rather than an effect-driven reset.
  const [isLoading, setIsLoading] = useState(() => Boolean(getToken()))

  useEffect(() => {
    setUnauthorizedHandler(() => setUser(null))
    return () => setUnauthorizedHandler(null)
  }, [])

  useEffect(() => {
    const token = getToken()
    if (!token) return
    fetchCurrentUser()
      .then(setUser)
      .catch(() => {
        clearToken()
        setUser(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  async function login(username: string, password: string) {
    const response = await loginRequest(username, password)
    setToken(response.access_token)
    setUser({ username: response.username, role: response.role })
  }

  function logout() {
    clearToken()
    setUser(null)
  }

  const value: AuthContextValue = { user, isLoading, login, logout }
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// Colocated with AuthProvider so callers have one import path; costs only
// Vite's Fast Refresh doing a full reload instead of a component-only one
// when this file changes, which doesn't justify splitting a one-line hook
// into its own file.
// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
