'use client'

import { createContext, useContext, useEffect, useMemo } from 'react'
import { useLocalStorageState } from '@/hooks/useLocalStorage'
import type { ReactNode } from 'react'
import { getJwtRole, isTokenExpired } from '@/services/jwt'
import { UNAUTHORIZED_EVENT } from '@/services/api'

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
  const expired = isTokenExpired(token)
  const role = expired ? null : getJwtRole(token)

  // A token surviving in localStorage past its 8h lifetime (see backend
  // ACCESS_TOKEN_EXPIRE_MINUTES) previously still read as "logged in" here,
  // so the header showed connected while every authenticated call 401'd
  // underneath it. Drop it as soon as we notice it's expired.
  useEffect(() => {
    if (token && expired) setTokenRaw(null)
  }, [token, expired, setTokenRaw])

  // Any authenticated request that comes back 401 (expired-but-undetected
  // clock skew, revoked token, server restart with a new secret, ...) should
  // log the user out immediately instead of leaving a dead token in place.
  useEffect(() => {
    function onUnauthorized() {
      setTokenRaw(null)
    }
    window.addEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
    return () => window.removeEventListener(UNAUTHORIZED_EVENT, onUnauthorized)
  }, [setTokenRaw])

  const isLoggedIn = Boolean(token) && !expired
  const value = useMemo<AuthContextValue>(
    () => ({ token: isLoggedIn ? token : null, isLoggedIn, role, isAdmin: role === 'admin', setToken: setTokenRaw }),
    [token, isLoggedIn, role, setTokenRaw],
  )
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
