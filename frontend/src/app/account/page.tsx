'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { getCurrentUser, updateCurrentUser, exportMyData, deleteMyAccount } from '@/services/auth'
import { useAuth } from '@/components/auth/AuthProvider'
import { ApiError } from '@/services/api'
import type { UserRead, UserUpdate } from '@/types/api'

export default function AccountPage() {
  const { isLoggedIn, setToken } = useAuth()
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

  async function onExport() {
    setError(null)
    try {
      const data = await exportMyData()
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'caribooks-mes-donnees.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Export impossible')
    }
  }

  async function onDelete() {
    const ok = window.confirm(
      'Supprimer définitivement votre compte ? Vos données personnelles seront effacées (anonymisées). ' +
        'Vos commandes sont conservées de façon anonyme pour des raisons légales. Cette action est irréversible.',
    )
    if (!ok) return
    setError(null)
    try {
      await deleteMyAccount()
      setToken(null)
      window.location.href = '/'
    } catch (e) {
      setError(e instanceof ApiError ? e.message : 'Suppression impossible')
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
      {error ? <div id="account-error" className="banner-error" role="alert">{error}</div> : null}
      <form className="card cardPadding" onSubmit={onSave}>
        <div className="two-up">
          <div>
            <label className="sr-only" htmlFor="acc-prenom">Prénom</label>
            <input id="acc-prenom" className="input" value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom" />
          </div>
          <div>
            <label className="sr-only" htmlFor="acc-nom">Nom</label>
            <input id="acc-nom" className="input" value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom" />
          </div>
        </div>
        <label className="sr-only" htmlFor="acc-email">Email</label>
        <input id="acc-email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" type="email" autoComplete="email" />

        <label className="sr-only" htmlFor="acc-billing1">Adresse (ligne 1)</label>
        <input id="acc-billing1" className="input" value={billing1} onChange={(e) => setBilling1(e.target.value)} placeholder="Adresse (ligne 1)" autoComplete="address-line1" />
        <label className="sr-only" htmlFor="acc-billing2">Adresse (ligne 2)</label>
        <input id="acc-billing2" className="input" value={billing2} onChange={(e) => setBilling2(e.target.value)} placeholder="Adresse (ligne 2)" autoComplete="address-line2" />
        <div className="two-up">
          <div>
            <label className="sr-only" htmlFor="acc-postal">Code postal</label>
            <input id="acc-postal" className="input" value={postal} onChange={(e) => setPostal(e.target.value)} placeholder="Code postal" autoComplete="postal-code" />
          </div>
          <div>
            <label className="sr-only" htmlFor="acc-city">Ville</label>
            <input id="acc-city" className="input" value={city} onChange={(e) => setCity(e.target.value)} placeholder="Ville" autoComplete="address-level2" />
          </div>
        </div>
        <div className="two-up">
          <div>
            <label className="sr-only" htmlFor="acc-country">Pays</label>
            <input id="acc-country" className="input" value={country} onChange={(e) => setCountry(e.target.value)} placeholder="Pays" autoComplete="country-name" />
          </div>
          <div>
            <label className="sr-only" htmlFor="acc-phone">Téléphone</label>
            <input id="acc-phone" className="input" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="Téléphone" type="tel" autoComplete="tel" />
          </div>
        </div>

        <label className="sr-only" htmlFor="acc-password">Nouveau mot de passe</label>
        <input
          id="acc-password"
          className="input"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          placeholder="Nouveau mot de passe (laisser vide pour conserver)"
          type="password"
          autoComplete="new-password"
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

      <section className="card cardPadding" aria-labelledby="rgpd-title" style={{ marginTop: 16 }}>
        <h2 id="rgpd-title" style={{ marginTop: 0, fontSize: '1.05rem' }}>Mes données personnelles</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          Conformément au RGPD et à la nLPD suisse, vous pouvez exporter vos données ou supprimer votre compte.{' '}
          <Link href="/confidentialite">Politique de confidentialité</Link>.
        </p>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button type="button" className="btn" onClick={onExport}>
            Exporter mes données (JSON)
          </button>
          <button type="button" className="btn" onClick={onDelete} style={{ color: 'var(--color-primary, #E51636)' }}>
            Supprimer mon compte
          </button>
        </div>
      </section>
    </div>
  )
}
