'use client'

import { createContext, useContext, useMemo } from 'react'
import { useLocalStorageState } from '@/hooks/useLocalStorage'
import type { ReactNode } from 'react'
import { getJwtRole } from '@/services/jwt'

type AuthContextValue = {
  token: string | null
  isLoggedIn: boolean
  role: string | null
  isAdmin: boolean
  setToken: (token: string | null) => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const { value: token, setValue: setTokenRaw } = useLocalStorageState<string | null>('caribooks_token', null)
  const role = getJwtRole(token)
  const value = useMemo<AuthContextValue>(
    () => ({ token, isLoggedIn: Boolean(token), role, isAdmin: role === 'admin', setToken: setTokenRaw }),
    [token, role, setTokenRaw],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
