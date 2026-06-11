'use client'

import { Suspense, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { ApiError } from '@/services/api'
import { login } from '@/services/auth'

function LoginForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get('returnTo') || '/'
  const { setToken } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
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

  return (
    <div className="content-center" style={{ maxWidth: 440 }}>
      <h1 style={{ margin: 0 }}>Connexion</h1>
      <form className="card cardPadding" onSubmit={onSubmit}>
        <input
          className="input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          type="email"
          autoComplete="email"
          required
        />
        <input
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe"
          type="password"
          autoComplete="current-password"
          required
        />
        {error ? <div className="banner-error">{error}</div> : null}
        <button className="btn btnPrimary" type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Connexion…' : 'Se connecter'}
        </button>
        <div className="muted" style={{ textAlign: 'center' }}>
          Pas de compte ?{' '}
          <Link href={`/register${returnTo !== '/' ? `?returnTo=${encodeURIComponent(returnTo)}` : ''}`}>
            Créer un compte
          </Link>
        </div>
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
