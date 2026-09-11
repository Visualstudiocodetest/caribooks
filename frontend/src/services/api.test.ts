import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiFetch, ApiError } from './api'

function jsonResponse(body: unknown, init: { status?: number } = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { 'content-type': 'application/json' },
  })
}

describe('apiFetch', () => {
  let fetchMock: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
    vi.stubGlobal('fetch', fetchMock)
    window.localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('routes browser requests through the /api/proxy rewrite', async () => {
    await apiFetch('/orders/commandes/73')
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/proxy/orders/commandes/73')
  })

  it('does not produce a double slash when path has a leading slash', async () => {
    await apiFetch('/health')
    const [url] = fetchMock.mock.calls[0]
    expect(url).toBe('/api/proxy/health')
  })

  it('always sets the Accept header to application/json', async () => {
    await apiFetch('/health')
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).get('Accept')).toBe('application/json')
  })

  it('sets Content-Type for a JSON string body', async () => {
    await apiFetch('/orders/commandes', { method: 'POST', body: JSON.stringify({ a: 1 }) })
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).get('Content-Type')).toBe('application/json')
  })

  it('does not force Content-Type for a FormData body', async () => {
    const fd = new FormData()
    fd.append('file', new Blob(['x']))
    await apiFetch('/upload', { method: 'POST', body: fd })
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).has('Content-Type')).toBe(false)
  })

  it('attaches the bearer token from localStorage when auth is requested', async () => {
    window.localStorage.setItem('caribooks_token', JSON.stringify('tok-123'))
    await apiFetch('/orders/commandes', { auth: true })
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).get('Authorization')).toBe('Bearer tok-123')
  })

  it('omits the Authorization header when no token is stored', async () => {
    await apiFetch('/orders/commandes', { auth: true })
    const [, options] = fetchMock.mock.calls[0]
    expect((options.headers as Headers).has('Authorization')).toBe(false)
  })

  it('returns the parsed JSON payload on success', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ id_commande: 73 }))
    const data = await apiFetch<{ id_commande: number }>('/orders/commandes/73')
    expect(data).toEqual({ id_commande: 73 })
  })

  it('throws an ApiError carrying the backend detail and status', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({ detail: 'Commande introuvable' }, { status: 404 }))
    const err = (await apiFetch('/orders/commandes/999').catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(404)
    expect(err.message).toBe('Commande introuvable')
  })

  it('falls back to a generic message when the error has no detail', async () => {
    fetchMock.mockResolvedValueOnce(jsonResponse({}, { status: 500 }))
    const err = (await apiFetch('/health').catch((e) => e)) as ApiError
    expect(err).toBeInstanceOf(ApiError)
    expect(err.message).toBe('API error (500)')
  })
})
