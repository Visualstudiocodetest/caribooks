'use client'

import { useEffect, useState } from 'react'
import { listAdminCommandes, adminAdvanceCommande, adminGetLignes, adminCancelCommande, adminRefundCommande, adminSetSent, adminSetAtReception, adminSetCommandeStatus } from '@/services/admin'
import { Money } from '@/components/ui/Money'
import { StatusBadge } from '@/components/ui/StatusBadge'
import { FORCE_STATUS_OPTIONS, statusLabel } from '@/lib/orderStatus'
import type { CommandeAdminRead, LigneCommandeAdminRead } from '@/types/api'

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

function ShippingBadge({ method }: { method?: string | null }) {
  const isPickup = (method || '').toUpperCase() === 'CLICK_COLLECT'
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700, background: isPickup ? '#1d4ed818' : '#7c3aed18', color: isPickup ? '#1d4ed8' : '#7c3aed', border: `1px solid ${isPickup ? '#1d4ed840' : '#7c3aed40'}`, whiteSpace: 'nowrap' }}>
      {isPickup ? 'Retrait en magasin' : 'La Poste'}
    </span>
  )
}

function OrderRow({ commande, onAdvanced, defaultExpanded }: { commande: CommandeAdminRead; onAdvanced: (c: Partial<CommandeAdminRead> & { id_commande: number }) => void; defaultExpanded?: boolean }) {
  const [busy, setBusy] = useState(false)
  const [expanded, setExpanded] = useState(defaultExpanded ?? false)
  const [lignes, setLignes] = useState<LigneCommandeAdminRead[] | null>(null)
  const [loadingLignes, setLoadingLignes] = useState(false)
  const [announcement, setAnnouncement] = useState<string | null>(null)
  const key = (commande.statut || '').toUpperCase()
  const isPaid = PAID_STATUSES.has(key)
  const isPost = (commande.shipping_method || 'POST').toUpperCase() === 'POST'
  const isTerminal = TERMINAL_STATUSES.has(key)
  const [overrideStatus, setOverrideStatus] = useState(key)

  // commande.statut can change from other actions on this row (Expédier,
  // Terminer, Annuler…) — without this, the dropdown kept showing whatever
  // status was selected at mount, so "Appliquer" could look enabled/disabled
  // against a status that was no longer current.
  useEffect(() => {
    setOverrideStatus(key)
  }, [key])

  async function runAction(fn: () => Promise<Partial<CommandeAdminRead> & { id_commande: number }>, doneMessage?: string) {
    setBusy(true)
    try {
      const result = await fn()
      onAdvanced(result)
      if (doneMessage) setAnnouncement(doneMessage)
    } finally {
      setBusy(false)
    }
  }

  function applyOverride() {
    if (overrideStatus === key) return
    if (!confirm(`Forcer le statut de ${commande.numero_commande} à « ${statusLabel(overrideStatus)} » ?\nCette action ignore le circuit normal de traitement.`)) return
    runAction(
      () => adminSetCommandeStatus(commande.id_commande, { statut: overrideStatus }),
      `Statut de la commande ${commande.numero_commande} mis à jour : ${statusLabel(overrideStatus)}.`,
    )
  }

  async function toggleExpand() {
    setExpanded((s) => !s)
    if (!lignes && !loadingLignes) {
      setLoadingLignes(true)
      try { setLignes(await adminGetLignes(commande.id_commande)) } finally { setLoadingLignes(false) }
    }
  }

  const clientName = [commande.client_prenom, commande.client_nom].filter(Boolean).join(' ')
  const rowBg = isPaid ? 'rgba(6,95,70,0.03)' : undefined
  const borderStyle = { borderBottom: '1px solid var(--color-border)' }
  const hasForceRow = !isTerminal
  const mainRowStyle = { background: rowBg, ...(!hasForceRow && !expanded ? borderStyle : {}) }
  const forceRowStyle = { background: rowBg, ...(!expanded ? borderStyle : {}) }
  const expandRowStyle = { background: rowBg, ...borderStyle }

  return (
    <>
      <tr style={mainRowStyle}>
        <td style={{ padding: '12px 8px', verticalAlign: 'top' }}>
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
        </td>
        <td style={{ padding: '12px 8px', verticalAlign: 'top' }}><Money amount={commande.montant_total_chf} /></td>
        <td style={{ padding: '12px 8px', verticalAlign: 'top' }}><StatusBadge statut={commande.statut || ''} /></td>
        <td style={{ padding: '12px 8px', verticalAlign: 'top' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
            {isPaid && isPost ? (
              <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
                onClick={() => runAction(() => adminSetSent(commande.id_commande), `Commande ${commande.numero_commande} marquée expédiée.`)}
                aria-label={`Marquer la commande ${commande.numero_commande} comme expédiée`}>
                {busy ? '…' : 'Expédier'}
              </button>
            ) : null}
            {isPaid && !isPost ? (
              <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
                onClick={() => runAction(() => adminSetAtReception(commande.id_commande), `Commande ${commande.numero_commande} prête au retrait.`)}
                aria-label={`Marquer la commande ${commande.numero_commande} comme prête au retrait`}>
                {busy ? '…' : 'Prêt au retrait'}
              </button>
            ) : null}
            {(key === 'SENT' || key === 'AT_RECEPTION') ? (
              <button className="btn btnPrimary" style={{ fontSize: 12, padding: '4px 10px' }} disabled={busy}
                onClick={() => runAction(() => adminAdvanceCommande(commande.id_commande) as Promise<CommandeAdminRead>, `Commande ${commande.numero_commande} terminée.`)}
                aria-label={`Terminer la commande ${commande.numero_commande}`}>
                {busy ? '…' : 'Terminer'}
              </button>
            ) : null}
            {!isPaid && !isTerminal ? (
              <button className="btn" style={{ fontSize: 12, padding: '4px 10px', color: '#dc2626', borderColor: '#dc262640' }} disabled={busy}
                onClick={() => { if (confirm('Annuler cette commande ?')) runAction(() => adminCancelCommande(commande.id_commande), `Commande ${commande.numero_commande} annulée.`) }}
                aria-label={`Annuler la commande ${commande.numero_commande}`}>
                {busy ? '…' : 'Annuler'}
              </button>
            ) : null}
            {isPaid && !isTerminal ? (
              <button className="btn" style={{ fontSize: 12, padding: '4px 10px', color: '#dc2626', borderColor: '#dc262640' }} disabled={busy}
                onClick={() => { if (confirm(`Rembourser ${commande.numero_commande} ?\nLe stock vendu sera restauré et le paiement marqué remboursé.`)) runAction(() => adminRefundCommande(commande.id_commande), `Commande ${commande.numero_commande} remboursée.`) }}
                aria-label={`Rembourser la commande ${commande.numero_commande}`}>
                {busy ? '…' : 'Rembourser'}
              </button>
            ) : null}
            <button
              className="btn"
              style={{ fontSize: 12, padding: '4px 10px' }}
              onClick={toggleExpand}
              aria-expanded={expanded}
              aria-label={expanded ? `Masquer les articles de la commande ${commande.numero_commande}` : `Afficher les articles de la commande ${commande.numero_commande}`}
            >
              {expanded ? 'Masquer' : 'Articles'}
            </button>
          </div>
          <div className="sr-only" role="status" aria-live="polite">{announcement}</div>
        </td>
      </tr>

      {hasForceRow ? (
        <tr style={forceRowStyle}>
          <td colSpan={4} style={{ padding: '0 8px 12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
              <label htmlFor={`force-status-${commande.id_commande}`} className="muted" style={{ fontSize: 11 }}>Forcer le statut :</label>
              <select
                id={`force-status-${commande.id_commande}`}
                className="input"
                style={{ fontSize: 12, padding: '3px 6px' }}
                value={overrideStatus}
                disabled={busy}
                onChange={(e) => setOverrideStatus(e.target.value)}
              >
                {FORCE_STATUS_OPTIONS.map((s) => (
                  <option key={s} value={s}>{statusLabel(s)}</option>
                ))}
              </select>
              <button
                className="btn"
                style={{ fontSize: 12, padding: '3px 10px' }}
                disabled={busy || overrideStatus === key}
                onClick={applyOverride}
                aria-label={`Appliquer le statut forcé à la commande ${commande.numero_commande}`}
              >
                Appliquer
              </button>
              <span className="muted" style={{ fontSize: 11 }}>
                (annulation/remboursement : utiliser les boutons dédiés ci-dessus, qui réconcilient le stock)
              </span>
            </div>
          </td>
        </tr>
      ) : null}

      {expanded ? (
        <tr style={expandRowStyle}>
          <td colSpan={4} style={{ padding: '0 8px 12px' }}>
            <h3 className="sr-only">Articles de la commande {commande.numero_commande}</h3>
            <div style={{ display: 'grid', gap: 4 }}>
              {loadingLignes ? (
                <div className="muted" style={{ fontSize: 13 }} role="status" aria-live="polite">Chargement…</div>
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
          </td>
        </tr>
      ) : null}
    </>
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
          Gestion des commandes
          {pendingCount > 0 ? (
            <span style={{ marginLeft: 10, background: '#b45309', color: 'white', borderRadius: 999, fontSize: 13, fontWeight: 700, padding: '2px 9px' }}>
              {pendingCount} en attente
            </span>
          ) : null}
        </h1>
      </div>

      {error ? <div className="banner-error" role="alert">{error}</div> : null}

      <h2 className="sr-only">Filtres</h2>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 200px' }}>
          <label htmlFor="admin-orders-search" className="sr-only">Rechercher par numéro de commande ou client</label>
          <input
            id="admin-orders-search"
            className="input"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Rechercher par numéro ou client…"
            style={{ width: '100%' }}
          />
        </div>
        <div role="group" aria-label="Filtrer les commandes par statut" style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {STATUS_FILTER_OPTIONS.map((o) => {
            const active = statusFilter === o.value
            const isPrep = o.value === 'prepare'
            return (
              <button
                key={o.value}
                className={active ? 'btn btnPrimary' : 'btn'}
                style={{ fontSize: 13, padding: '5px 14px', position: 'relative' }}
                onClick={() => setStatusFilter(o.value)}
                aria-pressed={active}
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

      <h2 className="sr-only">Liste des commandes</h2>
      <div className="card" style={{ padding: '0 4px' }}>
        {loading ? (
          <div className="muted" style={{ padding: 16 }} role="status" aria-live="polite">Chargement…</div>
        ) : filtered.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>
            {statusFilter === 'prepare' ? 'Aucune commande à préparer.' : 'Aucune commande'}
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Commande</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Montant</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Statut</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((c) => (
                <OrderRow
                  key={c.id_commande}
                  commande={c}
                  defaultExpanded={statusFilter === 'prepare'}
                  onAdvanced={(updated) => setCommandes((s) => s.map((x) => x.id_commande === updated.id_commande ? { ...x, ...updated } : x))}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
