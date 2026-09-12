'use client'

import Link from 'next/link'
import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { getCurrentUser } from '@/services/auth'

type Check = 'checking' | 'admin' | 'not-admin' | 'anon'

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { isLoggedIn } = useAuth()
  const router = useRouter()
  const pathname = usePathname()
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

  useEffect(() => {
    // Not connected at all: send straight to the login page with a message,
    // instead of rendering an inline "please log in" card in place of the
    // back-office. An authenticated-but-non-admin user is left on the
    // "Accès refusé" card below — sending them back to /login would just
    // show them the same account logged in again.
    if (check === 'anon') {
      router.replace(`/login?returnTo=${encodeURIComponent(pathname)}&reason=admin_required`)
    }
  }, [check, router, pathname])

  if (check === 'anon' || check === 'checking') {
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
