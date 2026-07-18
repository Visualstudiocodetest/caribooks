'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { useAuth } from '@/components/auth/AuthProvider'
import { getCurrentUser } from '@/services/auth'

type Check = 'checking' | 'admin' | 'not-admin' | 'anon'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth()
  // The role is NOT trusted from the client-side (unsigned) JWT decode. We verify
  // it against the backend, which validates the token signature and returns the
  // real role — so a tampered localStorage token can never render the back-office.
  const [check, setCheck] = useState<Check>('checking')

  useEffect(() => {
    let active = true
    if (!isLoggedIn) {
      setCheck('anon')
      return
    }
    setCheck('checking')
    getCurrentUser()
      .then((u) => active && setCheck(u.role === 'admin' ? 'admin' : 'not-admin'))
      .catch(() => active && setCheck('not-admin'))
    return () => {
      active = false
    }
  }, [isLoggedIn])

  if (check === 'anon') {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Connexion requise</div>
        <div className="muted">Connectez-vous avec un compte admin pour accéder au back-office.</div>
        <Link className="btn btnPrimary" href="/login?returnTo=/admin">
          Se connecter
        </Link>
      </div>
    )
  }

  if (check === 'checking') {
    return (
      <div className="card" style={{ padding: 16 }}>
        <div className="muted">Vérification des droits…</div>
      </div>
    )
  }

  if (check === 'not-admin') {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Accès refusé</div>
        <div className="muted">Ce back-office est réservé aux administrateurs.</div>
        <Link className="btn" href="/">
          Retour à l’accueil
        </Link>
      </div>
    )
  }

  return <>{children}</>
}
