'use client'

import { Suspense, useCallback, useEffect, useState } from 'react'

import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { ApiError } from '@/services/api'
import { googleLogin, login } from '@/services/auth'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'
import { safeReturnTo } from '@/lib/navigation'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = safeReturnTo(searchParams.get('returnTo'))
  const { isLoggedIn, setToken } = useAuth()

  useEffect(() => {
    if (isLoggedIn) router.replace(returnTo)
  }, [isLoggedIn, router, returnTo])
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!email.trim() || !password) {
      setError('Email et mot de passe requis.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const token = await login({ username: email.trim(), password })
      setToken(token.access_token)
      router.push(returnTo)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Email ou mot de passe incorrect.')
    } finally {
      setLoading(false)
    }
  }

  const handleGoogleCredential = useCallback(async (credential: string) => {
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
  }, [setToken, router, returnTo])

  return (
    <div className="content-center" style={{ maxWidth: 440 }}>
      <h1 style={{ margin: 0 }}>Connexion</h1>
      <form className="card cardPadding" onSubmit={onSubmit}>
        <label className="sr-only" htmlFor="login-email">Email</label>
        <input
          id="login-email"
          className="input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          type="email"
          autoComplete="email"
          required
          aria-describedby={error ? 'login-error' : undefined}
        />
        <label className="sr-only" htmlFor="login-password">Mot de passe</label>
        <input
          id="login-password"
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe"
          type="password"
          autoComplete="current-password"
          required
          aria-describedby={error ? 'login-error' : undefined}
        />
        {error ? <div id="login-error" className="banner-error" role="alert">{error}</div> : null}
        <button className="btn btnPrimary" type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Connexion…' : 'Se connecter'}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0' }}>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--color-border)' }} />
          <span className="muted" style={{ fontSize: '0.8rem' }}>ou</span>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--color-border)' }} />
        </div>
        <GoogleSignInButton onCredential={handleGoogleCredential} text="signin_with" />
      </form>
    </div>
  )
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginForm />
    </Suspense>
  )
}
