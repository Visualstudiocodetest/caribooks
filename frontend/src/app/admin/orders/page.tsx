'use client'

import { useEffect, useState } from 'react'
import { listAdminCommandes, adminAdvanceCommande, adminGetLignes } from '@/services/admin'
import { Money } from '@/components/ui/Money'
import type { CommandeRead, LigneCommandeRead } from '@/types/api'

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

const NEXT_STATUS_LABEL: Record<string, string> = {
  CREATED: 'Confirmer paiement',
  PENDING: 'Confirmer paiement',
  PAID: 'Faire avancer',
  CAPTURED: 'Faire avancer',
  COMPLETED: 'Faire avancer',
  SENT: 'Marquer livrée',
  AT_RECEPTION: 'Terminer',
}

const STATUS_FILTER_OPTIONS = [
  { value: '', label: 'Toutes' },
  { value: 'CREATED,PENDING', label: 'En attente' },
  { value: 'PAID,CAPTURED,COMPLETED', label: 'Payées' },
  { value: 'SENT', label: 'Expédiées' },
  { value: 'AT_RECEPTION', label: 'À retirer' },
  { value: 'FINISHED', label: 'Terminées' },
  { value: 'REFUNDED,FAILED,CANCELLED', label: 'Annulées / Remboursées' },
]

function StatusBadge({ statut }: { statut: string }) {
  const key = (statut || '').toUpperCase()
  const label = STATUS_LABELS[key] || statut
  const color = STATUS_COLORS[key] || '#6b7280'
  return (
    <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700, background: `${color}18`, color, border: `1px solid ${color}40`, whiteSpace: 'nowrap' }}>
      {label}
    </span>
  )
}

function OrderRow({ commande, onAdvanced }: { commande: CommandeRead; onAdvanced: (c: CommandeRead) => void }) {
  const [advancing, setAdvancing] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const [lignes, setLignes] = useState<LigneCommandeRead[] | null>(null)
  const [loadingLignes, setLoadingLignes] = useState(false)
  const key = (commande.statut || '').toUpperCase()
  const canAdvance = key in NEXT_STATUS_LABEL

  async function onAdvance() {
    setAdvancing(true)
    try {
      const updated = await adminAdvanceCommande(commande.id_commande)
      onAdvanced(updated)
    } finally {
      setAdvancing(false)
    }
  }

  async function toggleExpand() {
    setExpanded((s) => !s)
    if (!lignes && !loadingLignes) {
      setLoadingLignes(true)
      try {
        const data = await adminGetLignes(commande.id_commande)
        setLignes(data)
      } finally {
        setLoadingLignes(false)
      }
    }
  }

  return (
    <div style={{ borderBottom: '1px solid var(--color-border)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '12px 4px', flexWrap: 'wrap' }}>
        <div style={{ display: 'grid', gap: 3, minWidth: 0 }}>
          <div style={{ fontWeight: 800, fontSize: 14 }}>{commande.numero_commande}</div>
          <div className="muted" style={{ fontSize: 12 }}>
            {new Date(commande.date_commande).toLocaleDateString('fr-CH', { day: '2-digit', month: 'short', year: 'numeric' })}
            {' · '}
            {commande.shipping_method === 'CLICK_COLLECT' ? '🏪 Retrait' : '📬 Livraison'}
            {' · '}
            <span style={{ opacity: 0.6 }}>#{commande.id_utilisateur}</span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Money amount={commande.montant_total_chf} />
          <StatusBadge statut={commande.statut || ''} />
          {canAdvance ? (
            <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={advancing} onClick={onAdvance}>
              {advancing ? '…' : NEXT_STATUS_LABEL[key]}
            </button>
          ) : null}
          <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={toggleExpand}>
            {expanded ? 'Masquer' : 'Détails'}
          </button>
        </div>
      </div>

      {expanded ? (
        <div style={{ padding: '0 4px 12px', display: 'grid', gap: 4 }}>
          {loadingLignes ? (
            <div className="muted" style={{ fontSize: 13 }}>Chargement…</div>
          ) : lignes && lignes.length > 0 ? (
            lignes.map((l) => (
              <div key={l.id_ligne_commande} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '6px 10px' }}>
                <span>Article #{l.id_article} × {l.quantite}</span>
                <Money amount={l.prix_unitaire_chf * l.quantite} />
              </div>
            ))
          ) : (
            <div className="muted" style={{ fontSize: 13 }}>Aucun article trouvé.</div>
          )}
        </div>
      ) : null}
    </div>
  )
}

export default function AdminOrdersPage() {
  const [commandes, setCommandes] = useState<CommandeRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let mounted = true
    listAdminCommandes()
      .then((cs) => { if (mounted) setCommandes(cs) })
      .catch((e: unknown) => { setError((e as Error).message || 'Erreur de chargement') })
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  const filtered = commandes.filter((c) => {
    const key = (c.statut || '').toUpperCase()
    if (statusFilter) {
      const allowed = statusFilter.split(',')
      if (!allowed.includes(key)) return false
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      if (!c.numero_commande.toLowerCase().includes(q)) return false
    }
    return true
  })

  const pendingCount = commandes.filter((c) => ['CREATED', 'PENDING'].includes((c.statut || '').toUpperCase())).length

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>
          Commandes
          {pendingCount > 0 ? (
            <span style={{ marginLeft: 10, background: '#b45309', color: 'white', borderRadius: 999, fontSize: 13, fontWeight: 700, padding: '2px 9px' }}>
              {pendingCount}
            </span>
          ) : null}
        </h1>
      </div>

      {error ? <div className="banner-error">{error}</div> : null}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <input
          className="input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher par numéro…"
          style={{ flex: '1 1 200px' }}
        />
        <select className="input" value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ flex: '1 1 180px' }}>
          {STATUS_FILTER_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      <div className="card" style={{ padding: '0 12px' }}>
        {loading ? (
          <div className="muted" style={{ padding: 16 }}>Chargement…</div>
        ) : filtered.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>Aucune commande</div>
        ) : (
          filtered.map((c) => (
            <OrderRow
              key={c.id_commande}
              commande={c}
              onAdvanced={(updated) => setCommandes((s) => s.map((x) => x.id_commande === updated.id_commande ? updated : x))}
            />
          ))
        )}
      </div>
    </div>
  )
}
