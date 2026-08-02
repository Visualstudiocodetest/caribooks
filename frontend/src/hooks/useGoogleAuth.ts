'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { ApiError } from '@/services/api'
import { googleLogin } from '@/services/auth'
import { useAuth } from '@/components/auth/AuthProvider'

/**
 * Google credential → token exchange, shared by the login and register pages
 * (previously duplicated verbatim in both). Callers keep owning their own
 * loading/error state since it's shared with their regular submit flow.
 */
export function useGoogleAuth(
  returnTo: string,
  setError: (message: string | null) => void,
  setLoading: (loading: boolean) => void,
) {
  const router = useRouter()
  const { setToken } = useAuth()

  return useCallback(
    async (credential: string) => {
      setError(null)
      setLoading(true)
      try {
        const token = await googleLogin(credential)
        setToken(token.access_token)
        router.push(returnTo)
      } catch (e) {
        const err = e as unknown
        setError(err instanceof ApiError ? err.message : 'Connexion Google impossible.')
      } finally {
        setLoading(false)
      }
    },
    [returnTo, router, setToken, setError, setLoading],
  )
}
