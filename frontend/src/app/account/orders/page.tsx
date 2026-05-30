'use client'

import { useEffect, useState } from 'react'
import { getMyCommandes } from '@/services/orders'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import Link from 'next/link'
import type { CommandeRead } from '@/types/api'

export default function AccountOrdersPage() {
  const { isLoggedIn } = useAuth()
  const [loading, setLoading] = useState(true)
  const [commandes, setCommandes] = useState<CommandeRead[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    if (!isLoggedIn) {
      setLoading(false)
      return
    }
    setLoading(true)
    getMyCommandes()
      .then((list) => {
        if (!mounted) return
        setCommandes(list || [])
      })
      .catch((e: unknown) => {
        setError((e as Error).message || 'Impossible de charger les commandes')
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [isLoggedIn])

  if (!isLoggedIn) {
    return (
      <div className="card" style={{ padding: 16 }}>
        <div style={{ fontWeight: 800 }}>Authentification requise</div>
        <div className="muted">Connectez-vous pour voir vos commandes.</div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <Link className="btn btnPrimary" href="/login">
            Se connecter
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1>Mes commandes</h1>
      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="muted">{error}</div> : null}

      <div style={{ display: 'grid', gap: 12 }}>
        {commandes.length === 0 ? (
          <div className="card cardPadding">Aucune commande</div>
        ) : (
          commandes.map((c) => (
            <div className="card cardPadding" key={c.id_commande}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontWeight: 800 }}>{c.numero_commande}</div>
                  <div className="muted">{new Date(c.date_commande).toLocaleString()}</div>
                  <div className="muted">Méthode: {c.shipping_method || '—'}</div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <Money amount={c.montant_total_chf} />
                  <div className="muted">Statut: {c.statut || '—'}</div>
                </div>
              </div>

              <div style={{ marginTop: 8, display: 'flex', gap: 8 }}>
                <Link className="btn" href={`/account/orders/${c.id_commande}`}>
                  Détails
                </Link>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
