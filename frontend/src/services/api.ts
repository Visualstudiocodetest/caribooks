type ApiErrorPayload = {
  // FastAPI returns a plain string for HTTPException(detail=...), but a LIST of
  // per-field objects for a 422 request-validation error.
  detail?: string | unknown[]
}

// HTTP statuses the user can act on, phrased in French. Anything a route raises
// explicitly carries its own French `detail`; this only covers the responses
// FastAPI/the platform produce on their own (validation errors, gateway
// failures), which are English and were previously shown raw — or, for a 422,
// serialized as "[object Object]" because `detail` is a list there, not a string.
const STATUS_MESSAGES_FR: Record<number, string> = {
  400: 'Requête invalide.',
  401: 'Session expirée. Reconnectez-vous.',
  403: 'Vous n’avez pas les droits nécessaires pour cette action.',
  404: 'Ressource introuvable.',
  409: 'Cette action entre en conflit avec l’état actuel. Rechargez la page.',
  422: 'Certaines informations saisies sont invalides. Vérifiez le formulaire.',
  429: 'Trop de tentatives. Réessayez dans quelques minutes.',
  500: 'Une erreur est survenue. Réessayez dans un instant.',
  502: 'Service momentanément indisponible. Réessayez dans un instant.',
  503: 'Service momentanément indisponible. Réessayez dans un instant.',
  504: 'Le service met trop de temps à répondre. Réessayez dans un instant.',
}

function frenchMessageFor(status: number, detail: ApiErrorPayload['detail']): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  return STATUS_MESSAGES_FR[status] ?? 'Une erreur est survenue. Réessayez dans un instant.'
}

// Dispatched on window whenever an authenticated request comes back 401, so
// AuthProvider can clear the dead token and flip isLoggedIn immediately —
// instead of the UI still showing "connected" until the user happens to
// navigate somewhere else that also calls the API.
export const UNAUTHORIZED_EVENT = 'caribooks:unauthorized'

export class ApiError extends Error {
  status: number
  payload?: unknown

  constructor(message: string, status: number, payload?: unknown) {
    super(message)
    this.status = status
    this.payload = payload
  }
}

function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null
  const raw = window.localStorage.getItem('caribooks_token')
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as unknown
    return typeof parsed === 'string' ? parsed : raw
  } catch {
    return raw
  }
}

function getServerBackendBaseUrl(): string {
  // Server Components / Node runtime: call FastAPI directly (no CORS issue server-side)
  return process.env.BACKEND_BASE_URL || 'http://localhost:8000'
}

function getClientBackendBaseUrl(): string {
  // Browser runtime: route through the Next.js /api/proxy rewrite so the
  // request stays on the same origin — eliminates CORS entirely.
  // In local dev this proxies to NEXT_PUBLIC_BACKEND_BASE_URL via next.config.js.
  return '/api/proxy'
}

function joinUrl(base: string, path: string): string {
  return base.replace(/\/+$/, '') + path
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth, headers, ...rest } = options

  const mergedHeaders = new Headers(headers)
  mergedHeaders.set('Accept', 'application/json')

  const body = rest.body
  if (body && !(body instanceof FormData)) {
    if (!mergedHeaders.has('Content-Type')) mergedHeaders.set('Content-Type', 'application/json')
  }

  if (auth) {
    const token = getAuthToken()
    if (token) mergedHeaders.set('Authorization', `Bearer ${token}`)
  }

  const url =
    typeof window === 'undefined'
      ? joinUrl(getServerBackendBaseUrl(), path)
      : joinUrl(getClientBackendBaseUrl(), path)

  const fetchOptions: RequestInit = {
    ...rest,
    headers: mergedHeaders,
  }

  const res = await fetch(url, fetchOptions)

  const contentType = res.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined)

  if (!res.ok) {
    if (auth && res.status === 401 && typeof window !== 'undefined') {
      window.dispatchEvent(new Event(UNAUTHORIZED_EVENT))
    }
    const maybeDetail = (payload as ApiErrorPayload | undefined)?.detail
    throw new ApiError(frenchMessageFor(res.status, maybeDetail), res.status, payload)
  }

  return payload as T
}
