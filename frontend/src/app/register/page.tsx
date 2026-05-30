'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { ApiError } from '@/services/api'
import { register } from '@/services/auth'

export default function RegisterPage() {
  const router = useRouter()
  const [nom, setNom] = useState('')
  const [prenom, setPrenom] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [billingAddress1, setBillingAddress1] = useState('')
  const [billingAddress2, setBillingAddress2] = useState('')
  const [billingPostal, setBillingPostal] = useState('')
  const [billingCity, setBillingCity] = useState('')
  const [billingCountry, setBillingCountry] = useState('')
  const [billingPhone, setBillingPhone] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setLoading(true)
    try {
      await register({
        nom,
        prenom,
        email,
        mot_de_passe: password,
        billing_address_line1: billingAddress1 || undefined,
        billing_address_line2: billingAddress2 || undefined,
        billing_postal_code: billingPostal || undefined,
        billing_city: billingCity || undefined,
        billing_country: billingCountry || undefined,
        billing_phone: billingPhone || undefined,
      })
      router.push('/login')
    } catch (e) {
      const err = e as unknown
      setError(err instanceof ApiError ? err.message : 'Inscription impossible')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="content-center">
      <h1 style={{ margin: 0 }}>Créer un compte</h1>
      <form className="card cardPadding" onSubmit={onSubmit}>
        <div className="two-up">
          <input className="input" value={prenom} onChange={(e) => setPrenom(e.target.value)} placeholder="Prénom" />
          <input className="input" value={nom} onChange={(e) => setNom(e.target.value)} placeholder="Nom" />
        </div>
        <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
        <input className="input" value={billingAddress1} onChange={(e) => setBillingAddress1(e.target.value)} placeholder="Adresse (ligne 1)" />
        <input className="input" value={billingAddress2} onChange={(e) => setBillingAddress2(e.target.value)} placeholder="Adresse (ligne 2)" />
        <div className="two-up">
          <input className="input" value={billingPostal} onChange={(e) => setBillingPostal(e.target.value)} placeholder="Code postal" />
          <input className="input" value={billingCity} onChange={(e) => setBillingCity(e.target.value)} placeholder="Ville" />
        </div>
        <div className="two-up">
          <input className="input" value={billingCountry} onChange={(e) => setBillingCountry(e.target.value)} placeholder="Pays" />
          <input className="input" value={billingPhone} onChange={(e) => setBillingPhone(e.target.value)} placeholder="Téléphone" />
        </div>
        <input
          className="input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Mot de passe (min 6)"
          type="password"
        />
        {error ? <div className="muted">{error}</div> : null}
        <button className="btn btnPrimary" type="submit" disabled={loading}>
          {loading ? 'Création…' : 'Créer le compte'}
        </button>
        <div className="muted">
          Déjà un compte ? <Link href="/login">Se connecter</Link>
        </div>
      </form>
    </div>
  )
}
