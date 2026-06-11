'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getCurrentUser, updateCurrentUser } from '@/services/auth'
import { useAuth } from '@/components/auth/AuthProvider'
import { ApiError } from '@/services/api'
import type { UserRead, UserUpdate } from '@/types/api'

export default function AccountPage() {
  const { isLoggedIn } = useAuth()
  const [loading, setLoading] = useState(true)
  const [user, setUser] = useState<UserRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  const [prenom, setPrenom] = useState('')
  const [nom, setNom] = useState('')
  const [email, setEmail] = useState('')
  const [billing1, setBilling1] = useState('')
  const [billing2, setBilling2] = useState('')
  const [postal, setPostal] = useState('')
  const [city, setCity] = useState('')
  const [country, setCountry] = useState('')
  const [phone, setPhone] = useState('')
  const [newPassword, setNewPassword] = useState('')

  useEffect(() => {
    let mounted = true
    if (!isLoggedIn) {
      setLoading(false)
      return
    }
    setLoading(true)
    getCurrentUser()
      .then((u) => {
        if (!mounted) return
        setUser(u)
        setPrenom(String(u.prenom ?? ''))
        setNom(String(u.nom ?? ''))
        setEmail(String(u.email ?? ''))
        setBilling1(String(u.billing_address_line1 ?? ''))
        setBilling2(String(u.billing_address_line2 ?? ''))
        setPostal(String(u.billing_postal_code ?? ''))
        setCity(String(u.billing_city ?? ''))
        setCountry(String(u.billing_country ?? ''))
        setPhone(String(u.billing_phone ?? ''))
      })
      .catch((e) => {
        if (e instanceof ApiError) {
          // show structured payload when available
          const p = e.payload
          setError(typeof p === 'string' || p == null ? e.message : JSON.stringify(p))
        } else {
          setError('Impossible de charger le profil')
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [isLoggedIn])

  async function onSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setMessage(null)
    try {
      const payload: UserUpdate = {
        prenom,
        nom,
        email,
        billing_address_line1: billing1 || undefined,
        billing_address_line2: billing2 || undefined,
        billing_postal_code: postal || undefined,
        billing_city: city || undefined,
        billing_country: country || undefined,
        billing_phone: phone || undefined,
      }
      if (newPassword) payload.mot_de_passe = newPassword
      const updated = await updateCurrentUser(payload)
      setUser(updated)
      setMessage('Profil mis à jour')
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Impossible de sauvegarder')
    } finally {
      setSaving(false)
    }
  }

  if (!isLoggedIn) {
    return (
      <div className="card" style={{ padding: 16 }}>
        <div style={{ fontWeight: 800 }}>Authentification requise</div>
        <div className="muted">Connectez-vous pour voir et modifier votre profil.</div>
        <div style={{ display: 'flex', gap: 8, marginTop: 12 }}>
          <Link className="btn btnPrimary" href="/login">
            Se connecter
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="content-center">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <h1 style={{ margin: 0 }}>Mon compte</h1>
        <Link className="btn" href="/account/orders">Mes commandes</Link>
      </div>
      {loading ? <div className="muted">Chargement…</div> : null}
      {error ? <div className="banner-error">{error}</div> : null}
      <form className="card cardPadding" onSubmit={onSave}>
        <div className="two-up">
          <input className="input" value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom" />
          <input className="input" value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom" />
        </div>
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />

        <input className="input" value={billing1} onChange={(e) => setBilling1(e.target.value)} placeholder="Adresse (ligne 1)" />
        <input className="input" value={billing2} onChange={(e) => setBilling2(e.target.value)} placeholder="Adresse (ligne 2)" />
        <div className="two-up">
          <input className="input" value={postal} onChange={(e) => setPostal(e.target.value)} placeholder="Code postal" />
          <input className="input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Ville" />
        </div>
        <div className="two-up">
          <input className="input" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Pays" />
          <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Téléphone" />
        </div>

        <input
          className="input"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="Nouveau mot de passe (laisser vide pour conserver)"
          type="password"
        />

        {message ? <div className="banner-success">{message}</div> : null}

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="btn btnPrimary" type="submit" disabled={saving}>
            {saving ? 'Enregistrement…' : 'Enregistrer'}
          </button>
          <Link className="btn" href="/catalog">
            Retour au catalogue
          </Link>
        </div>
      </form>
    </div>
  )
}
