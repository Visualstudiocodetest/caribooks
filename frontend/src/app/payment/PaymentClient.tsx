'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { Money } from '@/components/ui/Money'
import { ApiError } from '@/services/api'
import type { CommandeRead } from '@/types/api'
import type {
  PostFinanceIframeCheckoutHandlerFactory,
  PostFinanceIframeHandler,
  PostFinancePaymentMethod,
} from '@/types/postfinance'
import {
  confirmPaiementPostFinance,
  createPaiementPostFinance,
  getCommande,
  pollPaiementPostFinance,
} from '@/services/orders'

function makeReference() {
  return `local-${Date.now()}`
}

export function paymentMethodLabel(method: PostFinancePaymentMethod): string {
  const resolved = method.resolvedTitle
  if (resolved) {
    return resolved['fr-CH'] || resolved['fr'] || resolved['en-US'] || method.name || `Méthode ${method.id}`
  }
  return method.name || `Méthode ${method.id}`
}

function loadPostFinanceScript(url: string): Promise<void> {
  return new Promise((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(`script[data-postfinance-js="${url}"]`)
    if (existing) {
      if (existing.dataset.loaded === 'true') {
        resolve()
        return
      }
      existing.addEventListener('load', () => resolve(), { once: true })
      existing.addEventListener('error', () => reject(new Error('PostFinance script failed to load')), { once: true })
      return
    }

    const script = document.createElement('script')
    script.src = url
    script.async = true
    script.dataset.postfinanceJs = url
    script.onload = () => {
      script.dataset.loaded = 'true'
      resolve()
    }
    script.onerror = () => reject(new Error('PostFinance script failed to load'))
    document.body.appendChild(script)
  })
}

const SUCCESS_STATUSES = new Set(['CAPTURED', 'PAID', 'COMPLETED', 'AUTHORIZED', 'FULFILL', 'SUCCESSFUL', 'FULFILLED'])

export function PaymentClient() {
  const searchParams = useSearchParams()
  const commandeId = Number(searchParams.get('commandeId'))
  const { isLoggedIn } = useAuth()

  const [commande, setCommande] = useState<CommandeRead | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [paymentMethods, setPaymentMethods] = useState<PostFinancePaymentMethod[]>([])
  const [selectedMethodId, setSelectedMethodId] = useState<number | null>(null)
  const [paiementId, setPaiementId] = useState<number | null>(null)
  const [localMode, setLocalMode] = useState(false)
  const [iframeReady, setIframeReady] = useState(false)
  const [iframeHeight, setIframeHeight] = useState(360)
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [paying, setPaying] = useState(false)
  const [payButtonLabel, setPayButtonLabel] = useState('Valider et payer')
  const [usePrimaryTrigger, setUsePrimaryTrigger] = useState(false)

  const handlerRef = useRef<PostFinanceIframeHandler | null>(null)
  const handlerMethodRef = useRef<number | null>(null)
  const paiementIdRef = useRef<number | null>(null)

  const ready = useMemo(
    () => isLoggedIn && Number.isFinite(commandeId) && commandeId > 0,
    [isLoggedIn, commandeId],
  )

  const mountIframe = useCallback(
  (methodId: number) => {
    const factory = (window as Window & { IframeCheckoutHandler?: PostFinanceIframeCheckoutHandlerFactory })
      .IframeCheckoutHandler
    if (!factory) {
      setError('Le script PostFinance n’est pas chargé.')
      return
    }

    if (handlerRef.current && handlerMethodRef.current === methodId) {
      return
    }

    // Destroy the previous handler before mounting a new one — otherwise
    // PostFinance appends a second iframe inside the existing container.
    if (handlerRef.current) {
      handlerRef.current.destroy?.()
      handlerRef.current = null
      handlerMethodRef.current = null
      const container = document.getElementById('postfinance-payment-form')
      if (container) container.innerHTML = ''
    }

    factory.configure?.('replacePrimaryAction', true)

    const handler = factory(methodId)
    handlerRef.current = handler
    handlerMethodRef.current = methodId
    setIframeReady(false)
    setValidationErrors([])
    setUsePrimaryTrigger(false)
    setPayButtonLabel('Valider et payer')

    handler.setValidationCallback((validationResult) => {
      setValidationErrors([])
      if (validationResult.success) {
        const currentPaiementId = paiementIdRef.current
        if (!currentPaiementId) {
          setError('Paiement introuvable.')
          setPaying(false)
          return
        }
        confirmPaiementPostFinance(currentPaiementId)
          .then(() => {
            handler.submit()
          })
          .catch((e: unknown) => {
            setPaying(false)
            setError(e instanceof ApiError ? e.message : 'Erreur lors de la confirmation du paiement.')
          })
      } else {
        setPaying(false)
        setValidationErrors(validationResult.errors || ['Informations de paiement invalides.'])
      }
    })

    handler.setInitializeCallback(() => {
      setIframeReady(true)
    })

    handler.setHeightChangeCallback((height) => {
      if (height > 0) {
        setIframeHeight(height)
      }
    })

    handler.setReplacePrimaryActionCallback((label) => {
      setPayButtonLabel(label)
      setUsePrimaryTrigger(true)
    })

    handler.setResetPrimaryActionCallback(() => {
      setPayButtonLabel('Valider et payer')
      setUsePrimaryTrigger(false)
    })

    handler.create('postfinance-payment-form')
  },
  [],
)

  useEffect(() => {
    if (!ready) return
    let mounted = true

    async function init() {
      setLoading(true)
      setError(null)

      try {
        const cmd = await getCommande(commandeId)
        if (!mounted) return
        setCommande(cmd)

        const statusParam = searchParams.get('status')
        const paiementIdParam = Number(searchParams.get('paiementId'))
        if (Number.isFinite(paiementIdParam) && paiementIdParam > 0) {
          const pollResp = await pollPaiementPostFinance(paiementIdParam)
          if (!mounted) return
          const statut = pollResp?.paiement?.statut
          if (statut && SUCCESS_STATUSES.has(String(statut).toUpperCase())) {
            window.location.href = '/account/orders'
            return
          }
          if (statusParam === 'failed') {
            setError('Le paiement a échoué. Vous pouvez réessayer.')
          } else {
            setError('Paiement en attente de confirmation. Réessayez ou contactez le support.')
          }
          return
        }

        const session = await createPaiementPostFinance({
          id_commande: cmd.id_commande,
          reference_externe: makeReference(),
          montant_chf: cmd.montant_total_chf,
          statut: 'PENDING',
        })
        if (!mounted) return

        if (session.error && !session.local_mode) {
          setError(session.error)
          return
        }

        paiementIdRef.current = session.paiement.id_paiement
        setPaiementId(session.paiement.id_paiement)
        setPaymentMethods(session.payment_methods || [])
        setLocalMode(Boolean(session.local_mode))

        const methods = session.payment_methods || []

        if (session.local_mode) {
          if (methods.length > 0) setSelectedMethodId(methods[0].id)
          return
        }

        if (!session.javascript_url) {
          setError('URL JavaScript PostFinance manquante.')
          return
        }

        // Load the script first — setSelectedMethodId would trigger the
        // selectedMethodId effect which calls mountIframe before IframeCheckoutHandler
        // is available on window, causing "Le script PostFinance n'est pas chargé".
        await loadPostFinanceScript(session.javascript_url)
        if (!mounted) return
        if (methods.length > 0) {
          setSelectedMethodId(methods[0].id)
          mountIframe(methods[0].id)
        }
      } catch (e: unknown) {
        if (!mounted) return
        setError(e instanceof ApiError ? e.message : 'Erreur paiement')
      } finally {
        if (mounted) {
          setLoading(false)
        }
      }
    }

    init()

    return () => {
      mounted = false
      handlerRef.current?.destroy?.()
      handlerRef.current = null
      handlerMethodRef.current = null
    }
  }, [commandeId, ready, searchParams, mountIframe])

  useEffect(() => {
    if (!selectedMethodId || localMode) return
    mountIframe(selectedMethodId)
  }, [selectedMethodId, localMode, mountIframe])

  async function onPayClick() {
    setPaying(true)
    setValidationErrors([])
    setError(null)

    if (localMode && paiementId) {
      try {
        await confirmPaiementPostFinance(paiementId)
        window.location.href = '/account/orders'
      } catch (e: unknown) {
        setPaying(false)
        setError(e instanceof ApiError ? e.message : 'Erreur lors du paiement local.')
      }
      return
    }

    const handler = handlerRef.current
    if (!handler) {
      setPaying(false)
      setError('Le formulaire de paiement n’est pas prêt.')
      return
    }

    if (usePrimaryTrigger) {
      handler.trigger()
      return
    }

    handler.validate()
  }

  if (!isLoggedIn) {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Connexion requise</div>
        <div className="muted">Connectez-vous pour effectuer le paiement.</div>
        <Link className="btn btnPrimary" href="/login">
          Se connecter
        </Link>
      </div>
    )
  }

  if (!Number.isFinite(commandeId) || commandeId <= 0) {
    return (
      <div className="card" style={{ padding: 16, display: 'grid', gap: 10 }}>
        <div style={{ fontWeight: 900 }}>Commande manquante</div>
        <div className="muted">Revenez au panier pour relancer une commande.</div>
        <Link className="btn btnPrimary" href="/cart">
          Aller au panier
        </Link>
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gap: 16, maxWidth: 820, margin: '0 auto' }}>
      <h1 style={{ margin: 0 }}>Paiement</h1>

      {loading ? <div className="muted">Chargement du formulaire de paiement…</div> : null}
      {error ? <div className="banner-error">{error}</div> : null}

      {commande ? (
        <div className="card" style={{ padding: 16, display: 'grid', gap: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
            <div>
              <div style={{ fontWeight: 900 }}>Commande</div>
              <div className="muted">{commande.numero_commande}</div>
            </div>
            <Money amount={commande.montant_total_chf} />
          </div>

          <div className="muted">
            Saisissez vos informations de paiement ci-dessous. Le paiement est traité par PostFinance Checkout.
          </div>

          {paymentMethods.length > 1 ? (
            <div style={{ display: 'grid', gap: 8 }}>
              <div style={{ fontWeight: 700 }}>Méthode de paiement</div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {paymentMethods.map((method) => (
                  <button
                    key={method.id}
                    type="button"
                    className={selectedMethodId === method.id ? 'btn btnPrimary' : 'btn'}
                    onClick={() => setSelectedMethodId(method.id)}
                    disabled={paying}
                  >
                    {paymentMethodLabel(method)}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {localMode ? (
            <div className="card" style={{ padding: 12 }}>
              <div style={{ fontWeight: 700 }}>Mode simulation locale</div>
              <div className="muted">
                PostFinance n’est pas configuré. Cliquez sur le bouton ci-dessous pour simuler un paiement réussi.
              </div>
            </div>
          ) : (
            <div
              id="postfinance-payment-form"
              style={{ minHeight: iframeHeight, border: '1px solid var(--border, #e5e7eb)', borderRadius: 8 }}
            />
          )}

          {validationErrors.length > 0 ? (
            <div className="banner-error">
              {validationErrors.map((msg) => (
                <div key={msg}>{msg}</div>
              ))}
            </div>
          ) : null}

          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <button
              className="btn btnPrimary"
              type="button"
              onClick={onPayClick}
              disabled={paying || loading || (!localMode && !iframeReady)}
            >
              {paying ? 'Traitement…' : payButtonLabel}
            </button>
            <Link className="btn" href="/catalog">
              Retour au catalogue
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  )
}
