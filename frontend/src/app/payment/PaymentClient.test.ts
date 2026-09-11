import { describe, expect, it, vi } from 'vitest'
import { paymentMethodLabel } from './PaymentClient'
import type { PostFinanceIframeHandler, PostFinancePaymentMethod } from '@/types/postfinance'

// ---------------------------------------------------------------------------
// paymentMethodLabel
// ---------------------------------------------------------------------------

describe('paymentMethodLabel', () => {
  it('prefers fr-CH from resolvedTitle', () => {
    const method: PostFinancePaymentMethod = {
      id: 1,
      name: 'Card',
      resolvedTitle: { 'fr-CH': 'Carte', 'en-US': 'Card' },
    }
    expect(paymentMethodLabel(method)).toBe('Carte')
  })

  it('falls back to fr when fr-CH is missing', () => {
    const method: PostFinancePaymentMethod = {
      id: 1,
      resolvedTitle: { fr: 'Carte', 'en-US': 'Card' },
    }
    expect(paymentMethodLabel(method)).toBe('Carte')
  })

  it('falls back to en-US when neither fr-CH nor fr is present', () => {
    const method: PostFinancePaymentMethod = { id: 1, resolvedTitle: { 'en-US': 'Card' } }
    expect(paymentMethodLabel(method)).toBe('Card')
  })

  it('falls back to name when resolvedTitle has no matching locale', () => {
    const method: PostFinancePaymentMethod = { id: 1, name: 'PostCard', resolvedTitle: {} }
    expect(paymentMethodLabel(method)).toBe('PostCard')
  })

  it('falls back to Méthode <id> when resolvedTitle and name are both absent', () => {
    const method: PostFinancePaymentMethod = { id: 42 }
    expect(paymentMethodLabel(method)).toBe('Méthode 42')
  })

  it('uses name directly when resolvedTitle is undefined', () => {
    const method: PostFinancePaymentMethod = { id: 1, name: 'Twint' }
    expect(paymentMethodLabel(method)).toBe('Twint')
  })
})

// ---------------------------------------------------------------------------
// PostFinance iframe handler lifecycle
//
// These tests verify the destroy-before-remount contract: switching to a
// different payment method must call destroy() on the previous handler and
// clear the container, so PostFinance does not append a second iframe.
// ---------------------------------------------------------------------------

function makeHandler(overrides: Partial<PostFinanceIframeHandler> = {}): PostFinanceIframeHandler {
  return {
    setValidationCallback: vi.fn(),
    setInitializeCallback: vi.fn(),
    setHeightChangeCallback: vi.fn(),
    setReplacePrimaryActionCallback: vi.fn(),
    setResetPrimaryActionCallback: vi.fn(),
    create: vi.fn(),
    validate: vi.fn(),
    submit: vi.fn(),
    trigger: vi.fn(),
    destroy: vi.fn(),
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// Script-load / mountIframe ordering (race condition guard)
//
// setSelectedMethodId must only be called AFTER the PostFinance script has
// loaded.  Calling it before the await means the selectedMethodId effect fires
// and invokes mountIframe while window.IframeCheckoutHandler is still undefined,
// producing "Le script PostFinance n'est pas chargé" even though the script
// eventually loads successfully.
// ---------------------------------------------------------------------------

describe('PostFinance script-load ordering', () => {
  it('does not invoke the factory before the script resolves', async () => {
    let resolveScript!: () => void
    const scriptPromise = new Promise<void>((res) => { resolveScript = res })

    const factory = vi.fn().mockReturnValue(makeHandler())
    const container = document.createElement('div')
    container.id = 'postfinance-payment-form'
    const state: { handler: PostFinanceIframeHandler | null; methodId: number | null } = {
      handler: null,
      methodId: null,
    }

    // Simulate: script starts loading, mountIframe should NOT be called yet
    const mountAfterLoad = scriptPromise.then(() => {
      simulateMountIframe(state, 510, container, factory)
    })

    expect(factory).not.toHaveBeenCalled()

    resolveScript()
    await mountAfterLoad

    expect(factory).toHaveBeenCalledOnce()
    expect(factory).toHaveBeenCalledWith(510)
  })
})

/**
 * Pure reimplementation of the guard/destroy block from mountIframe so we can
 * unit-test it without rendering the React component.
 */
function simulateMountIframe(
  state: { handler: PostFinanceIframeHandler | null; methodId: number | null },
  nextMethodId: number,
  container: HTMLElement,
  factory: (id: number) => PostFinanceIframeHandler,
) {
  if (state.handler && state.methodId === nextMethodId) {
    return // same method — no-op
  }

  if (state.handler) {
    state.handler.destroy?.()
    state.handler = null
    state.methodId = null
    container.innerHTML = ''
  }

  const handler = factory(nextMethodId)
  handler.create(container.id)
  state.handler = handler
  state.methodId = nextMethodId
}

describe('PostFinance iframe handler lifecycle', () => {
  it('does not recreate the handler when the same method is selected again', () => {
    const handler = makeHandler()
    const factory = vi.fn().mockReturnValue(makeHandler())
    const container = document.createElement('div')
    const state = { handler, methodId: 510 }

    simulateMountIframe(state, 510, container, factory)

    expect(factory).not.toHaveBeenCalled()
    expect(handler.destroy).not.toHaveBeenCalled()
    expect(state.handler).toBe(handler)
  })

  it('calls destroy on the old handler when switching to a different method', () => {
    const oldHandler = makeHandler()
    const newHandler = makeHandler()
    const factory = vi.fn().mockReturnValue(newHandler)
    const container = document.createElement('div')
    container.id = 'postfinance-payment-form'
    const state = { handler: oldHandler, methodId: 510 }

    simulateMountIframe(state, 511, container, factory)

    expect(oldHandler.destroy).toHaveBeenCalledOnce()
  })

  it('clears the container innerHTML before mounting the new handler', () => {
    const oldHandler = makeHandler()
    const container = document.createElement('div')
    container.id = 'postfinance-payment-form'
    container.innerHTML = '<iframe src="https://checkout.postfinance.ch/iframe"></iframe>'
    const state = { handler: oldHandler, methodId: 510 }

    simulateMountIframe(state, 511, container, () => makeHandler())

    expect(container.innerHTML).toBe('')
  })

  it('mounts the new handler in the container after destroying the old one', () => {
    const newHandler = makeHandler()
    const factory = vi.fn().mockReturnValue(newHandler)
    const container = document.createElement('div')
    container.id = 'postfinance-payment-form'
    const state = { handler: makeHandler(), methodId: 510 }

    simulateMountIframe(state, 511, container, factory)

    expect(factory).toHaveBeenCalledWith(511)
    expect(newHandler.create).toHaveBeenCalledWith('postfinance-payment-form')
    expect(state.handler).toBe(newHandler)
    expect(state.methodId).toBe(511)
  })

  it('mounts the first handler without calling destroy when there is no previous handler', () => {
    const handler = makeHandler()
    const factory = vi.fn().mockReturnValue(handler)
    const container = document.createElement('div')
    container.id = 'postfinance-payment-form'
    const state: { handler: PostFinanceIframeHandler | null; methodId: number | null } = {
      handler: null,
      methodId: null,
    }

    simulateMountIframe(state, 510, container, factory)

    expect(handler.destroy).not.toHaveBeenCalled()
    expect(handler.create).toHaveBeenCalledWith('postfinance-payment-form')
  })
})
