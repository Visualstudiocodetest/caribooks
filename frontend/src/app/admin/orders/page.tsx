'use client'

import { useEffect, useState } from 'react'
import { listAdminCommandes, adminAdvanceCommande, adminGetLignes, adminCancelCommande, adminSetSent, adminSetAtReception } from '@/services/admin'
import { Money } from '@/components/ui/Money'
import type { CommandeAdminRead, LigneCommandeAdminRead } from '@/types/api'
import { statusColor, statusLabel } from '@/lib/orderStatus'

const PAID_STATUSES = new Set(['PAID', 'CAPTURED', 'COMPLETED'])

const TERMINAL_STATUSES = new Set(['FINISHED', 'CANCELLED', 'REFUNDED'])

const STATUS_FILTER_OPTIONS = [
  { value: 'prepare', label: 'À préparer' },
  { value: '', label: 'Toutes' },
  { value: 'CREATED,PENDING', label: 'En attente' },
  { value: 'PAID,CAPTURED,COMPLETED', label: 'Payées' },
  { value: 'SENT', label: 'Expédiées' },
  { value: 'AT_RECEPTION', label: 'À retirer' },
  { value: 'FINISHED', label: 'Terminées' },
  { value: 'REFUNDED,FAILED,CANCELLED', label: 'Annulées / Remboursées' },
]

function StatusBadge({ statut }: { statut: string }) {
  const color = statusColor(statut)
  return (
    <span style={{ display: 'inline-block', padding: '2px 10px', borderRadius: 999, fontSize: 12, fontWeight: 700, background: `${color}18`, color, border: `1px solid ${color}40`, whiteSpace: 'nowrap' }}>
      {statusLabel(statut)}
    </span>
  )
}

function ShippingBadge({ method }: { method?: string | null }) {
  const isPickup = (method || '').toUpperCase() === 'CLICK_COLLECT'
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700, background: isPickup ? '#1d4ed818' : '#7c3aed18', color: isPickup ? '#1d4ed8' : '#7c3aed', border: `1px solid ${isPickup ? '#1d4ed840' : '#7c3aed40'}`, whiteSpace: 'nowrap' }}>
      {isPickup ? 'Retrait en magasin' : 'La Poste'}
    </span>
  )
}

function OrderRow({ commande, onAdvanced, defaultExpanded }: { commande: CommandeAdminRead; onAdvanced: (c: CommandeAdminRead) => void; defaultExpanded?: boolean }) {
  const [busy, setBusy] = useState(false)
  const [expanded, setExpanded] = useState(defaultExpanded ?? false)
  const [lignes, setLignes] = useState<LigneCommandeAdminRead[] | null>(null)
  const [loadingLignes, setLoadingLignes] = useState(false)
  const key = (commande.statut || '').toUpperCase()
  const isPaid = PAID_STATUSES.has(key)
  const isPost = (commande.shipping_method || 'POST').toUpperCase() === 'POST'
  const isTerminal = TERMINAL_STATUSES.has(key)

  async function runAction(fn: () => Promise<CommandeAdminRead>) {
    setBusy(true)
    try { onAdvanced(await fn()) } finally { setBusy(false) }
  }

  async function toggleExpand() {
    setExpanded((s) => !s)
    if (!lignes && !loadingLignes) {
      setLoadingLignes(true)
      try { setLignes(await adminGetLignes(commande.id_commande)) } finally { setLoadingLignes(false) }
    }
  }

  const clientName = [commande.client_prenom, commande.client_nom].filter(Boolean).join(' ')

  return (
    <div style={{ borderBottom: '1px solid var(--color-border)', background: isPaid ? 'rgba(6,95,70,0.03)' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12, padding: '12px 8px', flexWrap: 'wrap' }}>
        <div style={{ display: 'grid', gap: 3, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            <span style={{ fontWeight: 800, fontSize: 14 }}>{commande.numero_commande}</span>
            <ShippingBadge method={commande.shipping_method} />
          </div>
          <div className="muted" style={{ fontSize: 12 }}>
            {new Date(commande.date_commande).toLocaleDateString('fr-CH', { day: '2-digit', month: 'short', year: 'numeric' })}
            {clientName ? <> · <span style={{ fontWeight: 600, color: 'var(--color-text)' }}>{clientName}</span></> : null}
            {commande.client_email ? <> · {commande.client_email}</> : null}
          </div>
          {commande.client_adresse ? (
            <div className="muted" style={{ fontSize: 11 }}>{commande.client_adresse}</div>
          ) : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <Money amount={commande.montant_total_chf} />
          <StatusBadge statut={commande.statut || ''} />
          {isPaid && isPost ? (
            <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
              onClick={() => runAction(() => adminSetSent(commande.id_commande))}>
              {busy ? '…' : 'Expédier'}
            </button>
          ) : null}
          {isPaid && !isPost ? (
            <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
              onClick={() => runAction(() => adminSetAtReception(commande.id_commande))}>
              {busy ? '…' : 'Prêt au retrait'}
            </button>
          ) : null}
          {(key === 'SENT' || key === 'AT_RECEPTION') ? (
            <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
              onClick={() => runAction(() => adminAdvanceCommande(commande.id_commande) as Promise<CommandeAdminRead>)}>
              {busy ? '…' : 'Terminer'}
            </button>
          ) : null}
          {!isTerminal ? (
            <button className="btn" style={{ fontSize: 12, padding: '4px 10px', color: '#dc2626', borderColor: '#dc262640' }} disabled={busy}
              onClick={() => { if (confirm('Annuler cette commande ?')) runAction(() => adminCancelCommande(commande.id_commande)) }}>
              {busy ? '…' : 'Annuler'}
            </button>
          ) : null}
          <button className="btn" style={{ fontSize: 12, padding: '4px 10px' }} onClick={toggleExpand}>
            {expanded ? 'Masquer' : 'Articles'}
          </button>
        </div>
      </div>

      {expanded ? (
        <div style={{ padding: '0 8px 12px', display: 'grid', gap: 4 }}>
          {loadingLignes ? (
            <div className="muted" style={{ fontSize: 13 }}>Chargement…</div>
          ) : lignes && lignes.length > 0 ? (
            lignes.map((l) => (
              <div key={l.id_ligne_commande} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, fontSize: 13, background: 'var(--color-bg)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '6px 12px' }}>
                <div style={{ display: 'grid', gap: 1, minWidth: 0 }}>
                  <span style={{ fontWeight: 700 }}>{l.titre_article ?? `Article #${l.id_article}`}</span>
                  {l.sku_article ? <span className="muted" style={{ fontSize: 11 }}>SKU : {l.sku_article}</span> : null}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexShrink: 0 }}>
                  <span className="muted">× {l.quantite}</span>
                  <Money amount={l.prix_unitaire_chf * l.quantite} />
                </div>
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
  const [commandes, setCommandes] = useState<CommandeAdminRead[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('prepare')
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
    if (statusFilter === 'prepare') {
      if (!PAID_STATUSES.has(key)) return false
    } else if (statusFilter) {
      const allowed = statusFilter.split(',')
      if (!allowed.includes(key)) return false
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase()
      const clientName = `${c.client_prenom ?? ''} ${c.client_nom ?? ''}`.toLowerCase()
      if (!c.numero_commande.toLowerCase().includes(q) && !clientName.includes(q)) return false
    }
    return true
  })

  const prepareCount = commandes.filter((c) => PAID_STATUSES.has((c.statut || '').toUpperCase())).length
  const pendingCount = commandes.filter((c) => ['CREATED', 'PENDING'].includes((c.statut || '').toUpperCase())).length

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
        <h1 style={{ margin: 0 }}>
          Commandes
          {pendingCount > 0 ? (
            <span style={{ marginLeft: 10, background: '#b45309', color: 'white', borderRadius: 999, fontSize: 13, fontWeight: 700, padding: '2px 9px' }}>
              {pendingCount} en attente
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
          placeholder="Rechercher par numéro ou client…"
          style={{ flex: '1 1 200px' }}
        />
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {STATUS_FILTER_OPTIONS.map((o) => {
            const active = statusFilter === o.value
            const isPrep = o.value === 'prepare'
            return (
              <button
                key={o.value}
                className={active ? 'btn btnPrimary' : 'btn'}
                style={{ fontSize: 13, padding: '5px 14px', position: 'relative' }}
                onClick={() => setStatusFilter(o.value)}
              >
                {o.label}
                {isPrep && prepareCount > 0 ? (
                  <span style={{ marginLeft: 6, background: active ? 'rgba(255,255,255,0.3)' : '#065f46', color: 'white', borderRadius: 999, fontSize: 11, fontWeight: 700, padding: '1px 6px' }}>
                    {prepareCount}
                  </span>
                ) : null}
              </button>
            )
          })}
        </div>
      </div>

      <div className="card" style={{ padding: '0 4px' }}>
        {loading ? (
          <div className="muted" style={{ padding: 16 }}>Chargement…</div>
        ) : filtered.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>
            {statusFilter === 'prepare' ? 'Aucune commande à préparer.' : 'Aucune commande'}
          </div>
        ) : (
          filtered.map((c) => (
            <OrderRow
              key={c.id_commande}
              commande={c}
              defaultExpanded={statusFilter === 'prepare'}
              onAdvanced={(updated) => setCommandes((s) => s.map((x) => x.id_commande === updated.id_commande ? updated : x))}
            />
          ))
        )}
      </div>
    </div>
  )
}
