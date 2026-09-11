import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  confirmPaiementPostFinance,
  createCommande,
  createPaiementPostFinance,
  getCommande,
  getMyCommandes,
  pollPaiementPostFinance,
} from './orders'

const PROXY = '/api/proxy'

function jsonResponse(body: unknown) {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  })
}

describe('orders service', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    window.localStorage.setItem('caribooks_token', JSON.stringify('tok'))
    fetchMock = vi.fn().mockResolvedValue(jsonResponse({}))
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    window.localStorage.clear()
  })

  function lastCall() {
    const [url, options] = fetchMock.mock.calls.at(-1)!
    return { url: url as string, options: options as RequestInit }
  }

  it('getCommande GETs the commande by id with auth', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ id_commande: 73 }))
    const res = await getCommande(73)
    const { url, options } = lastCall()
    expect(url).toBe(`${PROXY}/orders/commandes/73`)
    expect(options.method ?? 'GET').toBe('GET')
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer tok')
    expect(res).toEqual({ id_commande: 73 })
  })

  it('createCommande POSTs the payload as JSON', async () => {
    await createCommande({ id_utilisateur: 1 } as never)
    const { url, options } = lastCall()
    expect(url).toBe(`${PROXY}/orders/commandes`)
    expect(options.method).toBe('POST')
    expect(options.body).toBe(JSON.stringify({ id_utilisateur: 1 }))
  })

  it('getMyCommandes GETs the commandes collection', async () => {
    await getMyCommandes()
    expect(lastCall().url).toBe(`${PROXY}/orders/commandes`)
  })

  it('createPaiementPostFinance POSTs to the postfinance endpoint', async () => {
    await createPaiementPostFinance({ id_commande: 73 } as never)
    const { url, options } = lastCall()
    expect(url).toBe(`${PROXY}/orders/paiements/postfinance`)
    expect(options.method).toBe('POST')
  })

  it('confirmPaiementPostFinance POSTs to the confirm endpoint for the payment', async () => {
    await confirmPaiementPostFinance(42)
    const { url, options } = lastCall()
    expect(url).toBe(`${PROXY}/orders/paiements/42/confirm-postfinance`)
    expect(options.method).toBe('POST')
  })

  it('pollPaiementPostFinance GETs the poll endpoint for the payment', async () => {
    await pollPaiementPostFinance(42)
    const { url, options } = lastCall()
    expect(url).toBe(`${PROXY}/orders/paiements/42/poll-postfinance`)
    expect(options.method ?? 'GET').toBe('GET')
  })
})
