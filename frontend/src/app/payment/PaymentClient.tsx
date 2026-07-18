'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from '@/components/auth/AuthProvider'
import { useCart } from '@/components/cart/CartProvider'
import { Money } from '@/components/ui/Money'
import { ApiError } from '@/services/api'
import type { CommandeRead } from '@/types/api'
import type {
  PostFinanceIframeCheckoutHandlerFactory,
  PostFinanceIframeHandler,
  PostFinancePaymentMethod,
} from '@/types/postfinance'
import {
  cancelCommande,
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
// Terminal PostFinance failure states — the card was refused, or the transaction
// was voided/declined. These are definitive (no point polling further).
const FAILURE_STATUSES = new Set(['FAILED', 'DECLINE', 'DECLINED', 'VOIDED', 'VOID'])

const sleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms))

export function PaymentClient() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const queryClient = useQueryClient()
  const commandeId = Number(searchParams.get('commandeId'))
  const { isLoggedIn } = useAuth()
  const { clear } = useCart()

  // After releasing a reservation (cancel / failed payment), the freed stock must
  // be reflected everywhere: invalidate the cached availability queries and refresh
  // the server components (catalogue) so the book is buyable again immediately.
  const refreshAvailability = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['availability'] })
    router.refresh()
  }, [queryClient, router])

  // Single place that marks a payment as done: empty the cart (so the paid items
  // can't be re-ordered) and switch to the success screen (which has no pay
  // button, so the customer can't be charged a second time). Stock is finalized
  // server-side by finalize_commande.
  const markPaymentSucceeded = useCallback(() => {
    clear()
    setPaying(false)
    setError(null)
    setPhase('success')
  }, [clear])

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
  const [cancelling, setCancelling] = useState(false)

  const [cartSecondsLeft, setCartSecondsLeft] = useState<number | null>(null)
  // 'form' = enter payment; 'confirming' = returned from PostFinance, verifying;
  // 'success' = paid (crystal-clear confirmation, no pay button so no double pay).
  // Initialise straight to 'confirming' when we land back from PostFinance (the URL
  // carries paiementId / status=failed) so the payment form never flashes.
  const [phase, setPhase] = useState<'form' | 'confirming' | 'success'>(() => {
    const pid = Number(searchParams.get('paiementId'))
    const returning = (Number.isFinite(pid) && pid > 0) || searchParams.get('status') === 'failed'
    return returning ? 'confirming' : 'form'
  })

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

    // Always destroy any previous handler AND clear the container before
    // mounting a new one — PostFinance appends a second iframe into the
    // existing container rather than replacing it. This must not be gated on
    // handlerRef.current being set: the effect cleanup below nulls that ref
    // without touching the DOM, so a subsequent mount would otherwise skip
    // clearing and leave the old iframe in place alongside the new one.
    handlerRef.current?.destroy?.()
    handlerRef.current = null
    handlerMethodRef.current = null
    const existingContainer = document.getElementById('postfinance-payment-form')
    if (existingContainer) existingContainer.innerHTML = ''

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

        // Helper: release the reservation + refresh availability so the book is
        // buyable again after a failed/abandoned payment. The cart keeps its items.
        const releaseAfterFailure = async () => {
          await cancelCommande(cmd.id_commande).catch(() => {})
          refreshAvailability()
        }

        // PostFinance redirected to the failed URL — definitive failure, no poll.
        if (statusParam === 'failed') {
          await releaseAfterFailure()
          setError(
            'Le paiement a été refusé ou annulé (carte invalide, fonds insuffisants, ou paiement interrompu). ' +
              'Vos articles sont toujours dans votre panier — vous pouvez réessayer.',
          )
          return
        }

        // Returned on the success URL (has paiementId). The transaction is often
        // still PROCESSING at redirect time, so poll for a resolved state instead
        // of reading a single check as "pending" (the old false-negative). The
        // webhook is the ultimate source of truth; this just gives quick feedback.
        if (Number.isFinite(paiementIdParam) && paiementIdParam > 0) {
          // We are back from PostFinance verifying the result — hide the payment
          // form so the customer cannot submit a second payment while we confirm.
          setPhase('confirming')
          const MAX_ATTEMPTS = 15
          for (let attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            if (!mounted) return
            let statut = ''
            try {
              const pollResp = await pollPaiementPostFinance(paiementIdParam)
              statut = String(pollResp?.paiement?.statut || '').toUpperCase()
            } catch {
              // transient — keep polling
            }
            if (!mounted) return

            if (SUCCESS_STATUSES.has(statut)) {
              markPaymentSucceeded()
              return
            }
            if (FAILURE_STATUSES.has(statut)) {
              await releaseAfterFailure()
              setError(
                'Le paiement a été refusé (carte invalide ou refusée). ' +
                  'Vos articles sont toujours dans votre panier — vous pouvez réessayer.',
              )
              return
            }
            // Reservation ran out while the user was on the PostFinance page.
            // Use the absolute expiry against the live clock so we catch expiry
            // that happens during this wait, not just an already-expired landing.
            const expired = cmd.cart_expires_at
              ? new Date(cmd.cart_expires_at).getTime() <= Date.now()
              : (cmd.cart_seconds_left ?? 1) <= 0
            if (expired) {
              setError(
                'Votre réservation a expiré avant la fin du paiement (délai de 20 minutes dépassé). ' +
                  'Les articles ont été remis en vente — reprenez votre commande depuis le panier.',
              )
              return
            }
            await sleep(2000)
          }
          // Still unresolved after ~30s: the webhook will finalize it shortly.
          setError(
            'Votre paiement est en cours de confirmation. Consultez « Mes commandes » dans un instant ; ' +
              'si le problème persiste, contactez le support.',
          )
          return
        }

        const session = await createPaiementPostFinance({
          id_commande: cmd.id_commande,
          reference_externe: makeReference(),
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
      const container = document.getElementById('postfinance-payment-form')
      if (container) container.innerHTML = ''
    }
    // Depend on the string form of searchParams, not the object itself — the
    // object's identity can change across renders without its content
    // changing, which previously re-ran this effect (re-creating a PostFinance
    // payment session and re-mounting the iframe) more often than intended.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [commandeId, ready, searchParams.toString(), mountIframe])

  useEffect(() => {
    if (!selectedMethodId || localMode) return
    mountIframe(selectedMethodId)
  }, [selectedMethodId, localMode, mountIframe])

  useEffect(() => {
    // Use the server-computed remaining seconds (timezone-proof) and count down
    // locally from there. Falls back to parsing cart_expires_at if absent.
    const initial =
      commande?.cart_seconds_left ??
      (commande?.cart_expires_at
        ? Math.floor((new Date(commande.cart_expires_at).getTime() - Date.now()) / 1000)
        : null)
    if (initial === null || initial === undefined) return
    const startedAt = Date.now()
    function tick() {
      const left = Math.floor((initial as number) - (Date.now() - startedAt) / 1000)
      setCartSecondsLeft(left > 0 ? left : 0)
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [commande?.cart_seconds_left, commande?.cart_expires_at])

  async function onPayClick() {
    setPaying(true)
    setValidationErrors([])
    setError(null)

    if (localMode && paiementId) {
      try {
        await confirmPaiementPostFinance(paiementId)
        markPaymentSucceeded()
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

  // Leaving checkout abandons this attempt: release the stock reservation so the
  // book is immediately buyable again. Two variants:
  //  - "Retour au catalogue": keep the cart (user may want to resume checkout).
  //  - "Annuler la commande": also empty the cart (user is giving up on it).
  // Both land back on the catalogue with fresh availability.
  const leaveCheckout = useCallback(
    async ({ clearCart }: { clearCart: boolean }) => {
      setCancelling(true)
      setError(null)
      try {
        await cancelCommande(commandeId)
        if (clearCart) clear()
        refreshAvailability()
        router.push('/catalog')
      } catch (e: unknown) {
        setCancelling(false)
        setError(e instanceof ApiError ? e.message : 'Erreur lors de l’annulation.')
      }
    },
    [commandeId, clear, refreshAvailability, router],
  )

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

  // Crystal-clear success confirmation — no pay button anywhere on this screen,
  // so the customer cannot be charged a second time. The cart is already emptied.
  if (phase === 'success') {
    return (
      <div style={{ display: 'grid', gap: 16, maxWidth: 640, margin: '0 auto' }}>
        <div className="card" style={{ padding: 24, display: 'grid', gap: 14, textAlign: 'center' }}>
          <div
            aria-hidden="true"
            style={{
              width: 64, height: 64, borderRadius: '50%', margin: '0 auto',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: '#065f4618', color: '#065f46', fontSize: 34, fontWeight: 900,
            }}
          >
            ✓
          </div>
          <h1 style={{ margin: 0, color: '#065f46' }}>Paiement réussi</h1>
          <div style={{ fontWeight: 700 }}>Merci, votre commande est confirmée.</div>
          {commande ? (
            <div className="muted">
              Commande {commande.numero_commande} — <Money amount={commande.montant_total_chf} />
            </div>
          ) : null}
          <div className="banner-success" role="status" style={{ fontWeight: 700 }}>
            Vous avez été débité une seule fois. Ne relancez pas le paiement.
          </div>
          <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link className="btn btnPrimary" href="/account/orders">Voir mes commandes</Link>
            <Link className="btn" href="/catalog">Continuer mes achats</Link>
          </div>
        </div>
      </div>
    )
  }

  // Returned from PostFinance: verifying the result. Show a clear "in progress"
  // state (or the resolved error) — but NEVER the payment form, so a second
  // payment can't be submitted while we confirm the first.
  if (phase === 'confirming') {
    return (
      <div style={{ display: 'grid', gap: 16, maxWidth: 640, margin: '0 auto' }}>
        <h1 style={{ margin: 0 }}>Paiement</h1>
        {error ? (
          <>
            <div className="banner-error">{error}</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <Link className="btn btnPrimary" href="/cart">Retour au panier</Link>
              <Link className="btn" href="/account/orders">Mes commandes</Link>
            </div>
          </>
        ) : (
          <div className="card cardPadding" role="status" style={{ display: 'grid', gap: 6 }}>
            <div style={{ fontWeight: 800 }}>Confirmation de votre paiement en cours…</div>
            <div className="muted">
              Merci de patienter, ne fermez pas cette page et ne relancez pas le paiement.
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div style={{ display: 'grid', gap: 16, maxWidth: 820, margin: '0 auto' }}>
      <h1 style={{ margin: 0 }}>Paiement</h1>

      {loading ? <div className="muted">Chargement du formulaire de paiement…</div> : null}
      {error ? <div className="banner-error">{error}</div> : null}
      {cartSecondsLeft !== null ? (
        <div
          className={cartSecondsLeft === 0 ? 'banner-error' : cartSecondsLeft <= 300 ? 'banner-warning' : 'card cardPadding'}
          style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 700 }}
        >
          {cartSecondsLeft === 0
            ? 'Votre réservation a expiré. Les articles ont été remis en vente.'
            : `⏱ Réservation valable encore ${Math.floor(cartSecondsLeft / 60)}:${String(cartSecondsLeft % 60).padStart(2, '0')}`}
        </div>
      ) : null}

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
            <button
              className="btn"
              type="button"
              onClick={() => leaveCheckout({ clearCart: true })}
              disabled={cancelling || paying}
            >
              {cancelling ? 'Annulation…' : 'Annuler la commande'}
            </button>
            <button
              className="btn"
              type="button"
              onClick={() => leaveCheckout({ clearCart: false })}
              disabled={cancelling || paying}
            >
              Retour au catalogue
            </button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
