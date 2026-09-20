'use client'

import { useEffect, useState } from 'react'
import { listUsers, setUserRole, deleteUser } from '@/services/users'
import { getCurrentUser } from '@/services/auth'
import type { UserRead } from '@/types/api'

export default function AdminUsersPage() {
  const [users, setUsers] = useState<UserRead[]>([])
  const [selfId, setSelfId] = useState<number | null>(null)
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [announcement, setAnnouncement] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    Promise.all([listUsers(), getCurrentUser()])
      .then(([u, me]) => {
        if (!mounted) return
        setUsers(u)
        setSelfId(me.id_utilisateur)
      })
      .catch((e: unknown) => setError((e as Error).message || 'Erreur de chargement'))
      .finally(() => { if (mounted) setLoading(false) })
    return () => { mounted = false }
  }, [])

  async function toggleAdmin(u: UserRead) {
    const nextRole = u.role === 'admin' ? 'user' : 'admin'
    const verb = nextRole === 'admin' ? 'promouvoir administrateur' : 'rétrograder en utilisateur simple'
    if (!confirm(`${verb === 'promouvoir administrateur' ? 'Promouvoir' : 'Rétrograder'} ${u.prenom} ${u.nom} (${u.email}) ?`)) return
    setBusyId(u.id_utilisateur)
    setError(null)
    try {
      const updated = await setUserRole(u.id_utilisateur, nextRole)
      setUsers((list) => list.map((x) => (x.id_utilisateur === u.id_utilisateur ? updated : x)))
      setAnnouncement(`Rôle mis à jour : ${u.prenom} ${u.nom} est maintenant ${nextRole === 'admin' ? 'administrateur' : 'utilisateur simple'}.`)
    } catch (e) {
      setError((e as Error).message || 'Action impossible')
    } finally {
      setBusyId(null)
    }
  }

  async function onDelete(u: UserRead) {
    if (!confirm(`Supprimer définitivement le compte de ${u.prenom} ${u.nom} (${u.email}) ?`)) return
    setBusyId(u.id_utilisateur)
    setError(null)
    try {
      await deleteUser(u.id_utilisateur)
      setUsers((list) => list.filter((x) => x.id_utilisateur !== u.id_utilisateur))
      setAnnouncement(`Compte de ${u.prenom} ${u.nom} supprimé.`)
    } catch (e) {
      setError((e as Error).message || 'Suppression impossible')
    } finally {
      setBusyId(null)
    }
  }

  const filtered = users.filter((u) => {
    if (!search.trim()) return true
    const q = search.trim().toLowerCase()
    return `${u.prenom} ${u.nom} ${u.email}`.toLowerCase().includes(q)
  })

  const adminCount = users.filter((u) => u.role === 'admin').length

  return (
    <div style={{ display: 'grid', gap: 16 }}>
      <h1 style={{ margin: 0 }}>
        Utilisateurs
        {users.length > 0 ? (
          <span className="muted" style={{ fontSize: 14, fontWeight: 600, marginLeft: 10 }}>
            {users.length} compte{users.length !== 1 ? 's' : ''} · {adminCount} admin{adminCount !== 1 ? 's' : ''}
          </span>
        ) : null}
      </h1>

      {error ? <div className="banner-error" role="alert">{error}</div> : null}
      <div className="sr-only" role="status" aria-live="polite">{announcement}</div>

      <div>
        <label htmlFor="admin-users-search" className="sr-only">Rechercher un utilisateur par nom ou email</label>
        <input
          id="admin-users-search"
          className="input"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Rechercher par nom ou email…"
          style={{ maxWidth: 360 }}
        />
      </div>

      <h2 className="sr-only">Liste des utilisateurs</h2>
      <div className="card" style={{ padding: '0 4px' }}>
        {loading ? (
          <div className="muted" style={{ padding: 16 }} role="status" aria-live="polite">Chargement…</div>
        ) : filtered.length === 0 ? (
          <div className="muted" style={{ padding: 16 }}>Aucun utilisateur</div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Nom</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Email</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Rôle</th>
                <th scope="col" style={{ textAlign: 'left', padding: '8px', fontSize: 12 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((u) => {
                const isSelf = u.id_utilisateur === selfId
                const isAdmin = u.role === 'admin'
                const busy = busyId === u.id_utilisateur
                return (
                  <tr key={u.id_utilisateur} style={{ borderBottom: '1px solid var(--color-border)' }}>
                    <td style={{ padding: '10px 8px', verticalAlign: 'middle' }}>
                      <span style={{ fontWeight: 700 }}>{u.prenom} {u.nom}</span>
                      {isSelf ? <span className="muted" style={{ fontSize: 11, marginLeft: 6 }}>(vous)</span> : null}
                    </td>
                    <td className="muted" style={{ padding: '10px 8px', fontSize: 12, verticalAlign: 'middle' }}>{u.email}</td>
                    <td style={{ padding: '10px 8px', verticalAlign: 'middle' }}>
                      <span
                        style={{
                          fontSize: 11,
                          fontWeight: 700,
                          padding: '1px 8px',
                          borderRadius: 999,
                          background: isAdmin ? '#7c3aed18' : '#37415118',
                          color: isAdmin ? '#7c3aed' : '#374151',
                        }}
                      >
                        {isAdmin ? 'admin' : 'utilisateur'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px', verticalAlign: 'middle' }}>
                      <div style={{ display: 'flex', gap: 8, flexShrink: 0, flexWrap: 'wrap' }}>
                        <button
                          className="btn"
                          style={{ fontSize: 12, padding: '4px 10px' }}
                          disabled={busy || isSelf}
                          title={isSelf ? 'Impossible de modifier votre propre rôle' : undefined}
                          onClick={() => toggleAdmin(u)}
                          aria-label={isAdmin ? `Rétrograder ${u.prenom} ${u.nom} en utilisateur simple` : `Promouvoir ${u.prenom} ${u.nom} administrateur`}
                        >
                          {busy ? '…' : isAdmin ? 'Rétrograder' : 'Promouvoir admin'}
                        </button>
                        <button
                          className="btn"
                          style={{ fontSize: 12, padding: '4px 10px', color: '#dc2626', borderColor: '#dc262640' }}
                          disabled={busy || isSelf}
                          title={isSelf ? 'Impossible de supprimer votre propre compte' : undefined}
                          onClick={() => onDelete(u)}
                          aria-label={`Supprimer le compte de ${u.prenom} ${u.nom}`}
                        >
                          Supprimer
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
