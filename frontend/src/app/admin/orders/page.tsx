'use client'

import { useEffect, useState } from 'react'
import { listAdminCommandes, adminAdvanceCommande } from '@/services/admin'
import { Money } from '@/components/ui/Money'
import type { CommandeRead } from '@/types/api'

const STATUS_LABELS: Record<string, string> = {
  CREATED: 'En attente',
  PENDING: 'En attente',
  PAID: 'Payée',
  CAPTURED: 'Payée',
  COMPLETED: 'Payée',
  SENT: 'Expédiée',
  AT_RECEPTION: 'Prête à retirer',
  FINISHED: 'Terminée',
  REFUNDED: 'Remboursée',
  FAILED: 'Échouée',
  CANCELLED: 'Annulée',
}

const STATUS_COLORS: Record<string, string> = {
  CREATED: '#b45309',
  PENDING: '#b45309',
  PAID: '#065f46',
  CAPTURED: '#065f46',
  COMPLETED: '#065f46',
  SENT: '#1d4ed8',
  AT_RECEPTION: '#1d4ed8',
  FINISHED: '#374151',
  REFUNDED: '#6b7280',
  FAILED: '#dc2626',
  CANCELLED: '#6b7280',
}

function StatusBadge({ statut }: { statut: string }) {
  const key = (statut || '').toUpperCase()
  const label = STATUS_LABELS[key] || statut
  const color = STATUS_COLORS[key] || '#6b7280'
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
        whiteSpace: 'nowrap',
      }}
    >
      {label}
    </span>
  )
}

const NEXT_STATUS: Record<string, string> = {
  PAID: 'Marquer expédiée',
  CAPTURED: 'Marquer expédiée',
  COMPLETED: 'Marquer expédiée',
  SENT: 'Marquer retirée',
  AT_RECEPTION: 'Terminer',
}

export default function AdminOrdersPage() {
  const [commandes, setCommandes] = useState<CommandeRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [advancing, setAdvancing] = useState<number | null>(null)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    listAdminCommandes()
      .then((cs) => { if (mounted) setCommandes(cs) })
      .catch((e: unknown) => { setError((e as Error).message || 'Erreur de chargement') })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  async function onAdvance(id: number) {
    setAdvancing(id)
    try {
      const updated = await adminAdvanceCommande(id)
      setCommandes((s) => s.map((c) => (c.id_commande === updated.id_commande ? updated : c)))
    } catch (e) {
      setError((e as Error).message || 'Impossible de faire avancer la commande')
    } finally {
      setAdvancing(null)
    }
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h1 style={{ margin: 0 }}>Commandes</h1>

      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="banner-error">{error}</div> : null}

      <div className="card" style={{ padding: 12 }}>
        {!loading && commandes.length === 0 ? (
          <div className="muted">Aucune commande</div>
        ) : (
          <div style={{ display: 'grid', gap: 0 }}>
            {commandes.map((c, i) => {
              const key = (c.statut || '').toUpperCase()
              const canAdvance = key in NEXT_STATUS
              return (
                <div
                  key={c.id_commande}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px 4px',
                    borderBottom: i < commandes.length - 1 ? '1px solid var(--color-border)' : 'none',
                    flexWrap: 'wrap',
                  }}
                >
                  <div style={{ display: 'grid', gap: 4 }}>
                    <div style={{ fontWeight: 800, fontSize: 14 }}>{c.numero_commande}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {new Date(c.date_commande).toLocaleDateString('fr-CH', {
                        day: '2-digit', month: 'short', year: 'numeric',
                      })}
                      {' · '}
                      {c.shipping_method === 'CLICK_COLLECT' ? 'Retrait' : 'Livraison'}
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
                    <Money amount={c.montant_total_chf} />
                    <StatusBadge statut={c.statut || ''} />
                    {canAdvance ? (
                      <button
                        className="btn btnPrimary"
                        style={{ fontSize: 12, padding: '4px 10px' }}
                        disabled={advancing === c.id_commande}
                        onClick={() => onAdvance(c.id_commande)}
                      >
                        {advancing === c.id_commande ? '…' : NEXT_STATUS[key]}
                      </button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
