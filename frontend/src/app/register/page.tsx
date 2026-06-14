'use client'

import { Suspense, useCallback, useState } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { ApiError } from '@/services/api'
import { googleLogin, register, login } from '@/services/auth'
import { useAuth } from '@/components/auth/AuthProvider'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'

function RegisterForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const returnTo = searchParams.get('returnTo') || '/'
  const { setToken } = useAuth()
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

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

  async function onSubmit(e: { preventDefault(): void }) {
    e.preventDefault()
    if (!prenom.trim() || !nom.trim()) {
      setError('Prénom et nom requis.')
      return
    }
    if (!email.trim()) {
      setError('Email requis.')
      return
    }
    if (password.length < 6) {
      setError('Le mot de passe doit contenir au moins 6 caractères.')
      return
    }
    setError(null)
    setLoading(true)
    try {
      await register({ nom, prenom, email: email.trim(), mot_de_passe: password })
      const token = await login({ username: email.trim(), password })
      setToken(token.access_token)
      router.push(returnTo)
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Inscription impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="content-center" style={{ maxWidth: 440 }}>
      <h1 style={{ margin: 0 }}>Créer un compte</h1>
      <form className="card cardPadding" onSubmit={onSubmit}>
        <div className="two-up">
          <div>
            <label className="sr-only" htmlFor="reg-prenom">Prénom</label>
            <input
              id="reg-prenom"
              className="input"
              value={prenom}
              onChange={(e) => setPrenom(e.target.value)}
              placeholder="Prénom"
              autoComplete="given-name"
              required
            />
          </div>
          <div>
            <label className="sr-only" htmlFor="reg-nom">Nom</label>
            <input
              id="reg-nom"
              className="input"
              value={nom}
              onChange={(e) => setNom(e.target.value)}
              placeholder="Nom"
              autoComplete="family-name"
              required
            />
          </div>
        </div>
        <label className="sr-only" htmlFor="reg-email">Email</label>
        <input
          id="reg-email"
          className="input"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="Email"
          type="email"
          autoComplete="email"
          required
          aria-describedby={error ? 'reg-error' : undefined}
        />
        <label className="sr-only" htmlFor="reg-password">Mot de passe</label>
        <input
          id="reg-password"
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe (min. 6 caractères)"
          type="password"
          autoComplete="new-password"
          minLength={6}
          required
          aria-describedby={error ? 'reg-error' : undefined}
        />
        {error ? <div id="reg-error" className="banner-error" role="alert">{error}</div> : null}
        <button className="btn btnPrimary" type="submit" disabled={loading} style={{ width: '100%' }}>
          {loading ? 'Création…' : 'Créer le compte'}
        </button>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, margin: '4px 0' }}>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--color-border)' }} />
          <span className="muted" style={{ fontSize: '0.8rem' }}>ou</span>
          <hr style={{ flex: 1, border: 'none', borderTop: '1px solid var(--color-border)' }} />
        </div>
        <GoogleSignInButton onCredential={handleGoogleCredential} text="signup_with" />
        <div className="muted" style={{ textAlign: 'center' }}>
          Vous pourrez renseigner votre adresse de livraison dans votre profil.
        </div>
        <div className="muted" style={{ textAlign: 'center' }}>
          Déjà un compte ? <Link href="/login">Se connecter</Link>
        </div>
      </form>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  )
}
