'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMyCommandes } from '@/services/orders'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import { StatusBadge } from '@/components/ui/StatusBadge'
import type { CommandeRead } from '@/types/api'

export default function AccountOrdersPage() {
  const { isLoggedIn } = useAuth()
  const [loading, setLoading] = useState(true)
  const [commandes, setCommandes] = useState<CommandeRead[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    if (!isLoggedIn) { setLoading(false); return }
    setLoading(true)
    getMyCommandes()
      .then((list) => {
        if (!mounted) return
        // Most recent first (by order date, newest → oldest).
        const sorted = [...(list || [])].sort(
          (a, b) => new Date(b.date_commande).getTime() - new Date(a.date_commande).getTime(),
        )
        setCommandes(sorted)
      })
      .catch((e: unknown) => { setError((e as Error).message || 'Impossible de charger les commandes') })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [isLoggedIn])

  if (!isLoggedIn) {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 800 }}>Authentification requise</div>
        <Link className="btn btnPrimary" href="/login?returnTo=/account/orders">Se connecter</Link>
      </div>
    )
  }

  return (
    <div className="content-center">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <h1 style={{ margin: 0 }}>Mes commandes</h1>
        <Link className="btn" href="/account">Mon profil</Link>
      </div>

      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="banner-error" role="alert">{error}</div> : null}

      {!loading && !error && (
        commandes.length === 0 ? (
          <div className="card cardPadding" style={{ textAlign: 'center' }}>
            <div className="muted">Vous n&apos;avez pas encore de commande.</div>
            <Link className="btn btnPrimary" href="/" style={{ marginTop: 10 }}>
              Voir le catalogue
            </Link>
          </div>
        ) : (
          <ul style={{ display: 'grid', gap: 10, listStyle: 'none', margin: 0, padding: 0 }}>
            {commandes.map((c) => (
              <li className="card cardPadding" key={c.id_commande}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ display: 'grid', gap: 4 }}>
                    <div style={{ fontWeight: 800 }}>
                      <span className="sr-only">Commande n° </span>
                      {c.numero_commande}
                    </div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      <span className="sr-only">Date de commande : </span>
                      {new Date(c.date_commande).toLocaleDateString('fr-CH', {
                        day: '2-digit', month: 'long', year: 'numeric',
                      })}
                    </div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      <span className="sr-only">Mode de livraison : </span>
                      {c.shipping_method === 'CLICK_COLLECT' ? 'Retrait en magasin' : 'Livraison postale'}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', display: 'grid', gap: 6 }}>
                    <div>
                      <span className="sr-only">Total : </span>
                      <Money amount={c.montant_total_chf} />
                    </div>
                    <div>
                      <span className="sr-only">Statut : </span>
                      <StatusBadge statut={c.statut || ''} />
                    </div>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )
      )}
    </div>
  )
}
