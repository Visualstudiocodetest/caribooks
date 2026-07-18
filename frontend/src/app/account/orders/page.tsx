'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getMyCommandes } from '@/services/orders'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import type { CommandeRead } from '@/types/api'
import { statusColor, statusLabel } from '@/lib/orderStatus'

function StatusBadge({ statut }: { statut: string }) {
  const label = statusLabel(statut)
  const color = statusColor(statut)
  return (
    <span
      style={{
        display: 'inline-block',
        padding: '2px 10px',
        borderRadius: '999px',
        fontSize: 12,
        fontWeight: 700,
        background: `${color}18`,
        color,
        border: `1px solid ${color}40`,
      }}
    >
      {label}
    </span>
  )
}

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
      {error ? <div className="banner-error">{error}</div> : null}

      {!loading && !error && (
        <div style={{ display: 'grid', gap: 10 }}>
          {commandes.length === 0 ? (
            <div className="card cardPadding" style={{ textAlign: 'center' }}>
              <div className="muted">Vous n'avez pas encore de commande.</div>
              <Link className="btn btnPrimary" href="/catalog" style={{ marginTop: 10 }}>
                Voir le catalogue
              </Link>
            </div>
          ) : (
            commandes.map((c) => (
              <div className="card cardPadding" key={c.id_commande}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12, flexWrap: 'wrap' }}>
                  <div style={{ display: 'grid', gap: 4 }}>
                    <div style={{ fontWeight: 800 }}>{c.numero_commande}</div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {new Date(c.date_commande).toLocaleDateString('fr-CH', {
                        day: '2-digit', month: 'long', year: 'numeric',
                      })}
                    </div>
                    <div className="muted" style={{ fontSize: 13 }}>
                      {c.shipping_method === 'CLICK_COLLECT' ? 'Retrait en magasin' : 'Livraison postale'}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right', display: 'grid', gap: 6 }}>
                    <Money amount={c.montant_total_chf} />
                    <StatusBadge statut={c.statut || ''} />
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  )
}
