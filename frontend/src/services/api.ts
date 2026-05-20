type ApiErrorPayload = {
  detail?: string
}

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
  // Browser runtime: call FastAPI directly (requires CORS on backend)
  return process.env.NEXT_PUBLIC_BACKEND_BASE_URL || process.env.BACKEND_BASE_URL || 'http://localhost:8000'
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

  const res = await fetch(url, {
    ...rest,
    headers: mergedHeaders,
  })

  const contentType = res.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')
  const payload = isJson ? await res.json().catch(() => undefined) : await res.text().catch(() => undefined)

  if (!res.ok) {
    const maybeDetail = (payload as ApiErrorPayload | undefined)?.detail
    throw new ApiError(maybeDetail || `API error (${res.status})`, res.status, payload)
  }

  return payload as T
}
