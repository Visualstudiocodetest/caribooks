'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'

const STORAGE_KEY = 'caribooks_cookie_consent'

type ConsentState = 'accepted' | 'refused' | null

export function CookieBanner() {
  const [consent, setConsent] = useState<ConsentState>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY) as ConsentState | null
    if (!stored) {
      setVisible(true)
    } else {
      setConsent(stored)
    }
  }, [])

  function handleAccept() {
    localStorage.setItem(STORAGE_KEY, 'accepted')
    setConsent('accepted')
    setVisible(false)
  }

  function handleRefuse() {
    localStorage.setItem(STORAGE_KEY, 'refused')
    setConsent('refused')
    setVisible(false)
  }

  if (!visible || consent !== null) return null

  return (
    <div
      role="dialog"
      aria-label="Consentement aux cookies"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 1000,
        backgroundColor: 'var(--color-bg, #fff)',
        borderTop: '1px solid var(--color-border)',
        padding: '16px 24px',
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 12,
        boxShadow: '0 -2px 12px rgba(0,0,0,0.08)',
      }}
    >
      <p style={{ margin: 0, flex: '1 1 300px', fontSize: '0.9rem' }}>
        Nous utilisons des cookies strictement nécessaires au fonctionnement du site ainsi que des
        cookies analytiques (Vercel Speed Insights) pour améliorer votre expérience. Consultez
        notre{' '}
        <Link href="/confidentialite" style={{ textDecoration: 'underline' }}>
          politique de confidentialité
        </Link>
        .
      </p>
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          className="btn"
          onClick={handleRefuse}
          style={{ padding: '8px 16px', fontSize: '0.875rem' }}
        >
          Refuser
        </button>
        <button
          className="btn btnPrimary"
          onClick={handleAccept}
          style={{ padding: '8px 16px', fontSize: '0.875rem' }}
        >
          Accepter
        </button>
      </div>
    </div>
  )
}
