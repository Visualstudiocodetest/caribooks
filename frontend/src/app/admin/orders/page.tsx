'use client'

import { useEffect, useState } from 'react'
import { listAdminCommandes, adminAdvanceCommande } from '@/services/admin'
import type { CommandeRead } from '@/types/api'

export default function AdminOrdersPage() {
  const [commandes, setCommandes] = useState<CommandeRead[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    listAdminCommandes()
      .then((cs) => {
        if (!mounted) return
        setCommandes(cs)
      })
      .finally(() => {
        if (!mounted) return
        setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  async function onAdvance(id: number) {
    try {
      const updated = await adminAdvanceCommande(id)
      setCommandes((s) => s.map((c) => (c.id_commande === updated.id_commande ? updated : c)))
    } catch (e) {
      // ignore for now
    }
  }

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h1 style={{ margin: 0 }}>Commandes (admin)</h1>
      {loading ? <div className="muted">Chargement…</div> : null}
      <div className="card" style={{ padding: 12 }}>
        {commandes.length === 0 ? (
          <div className="muted">Aucune commande</div>
        ) : (
          <div style={{ display: 'grid', gap: 8 }}>
            {commandes.map((c) => (
              <div key={c.id_commande} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 800 }}>{c.numero_commande}</div>
                  <div className="muted">{c.montant_total_chf} CHF — {c.statut}</div>
                </div>
                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn" onClick={() => onAdvance(c.id_commande)}>Avancer</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
