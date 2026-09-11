function base64UrlDecode(input: string): string {
  const normalized = input.replace(/-/g, '+').replace(/_/g, '/')
  const pad = normalized.length % 4
  const padded = pad ? normalized + '='.repeat(4 - pad) : normalized
  if (typeof window === 'undefined') {
    return Buffer.from(padded, 'base64').toString('utf-8')
  }
  return decodeURIComponent(
    Array.prototype.map
      .call(atob(padded), (c: string) => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join(''),
  )
}

export function decodeJwtPayload(token: string): unknown {
  const parts = token.split('.')
  if (parts.length < 2) return null
  try {
    return JSON.parse(base64UrlDecode(parts[1]))
  } catch {
    return null
  }
}

export function getJwtRole(token: string | null): string | null {
  if (!token) return null
  const payload = decodeJwtPayload(token) as { role?: unknown } | null
  const role = payload?.role
  return typeof role === 'string' ? role : null
}

// Backend tokens always carry an `exp` claim (see jwt_service.create_access_token).
// Without this check, a token left in localStorage past its 8h lifetime still
// reads as "logged in" client-side until an API call 401s — showing a stale
// "connected" header while every authenticated request fails underneath it.
export function isTokenExpired(token: string | null): boolean {
  if (!token) return true
  const payload = decodeJwtPayload(token) as { exp?: unknown } | null
  const exp = typeof payload?.exp === 'number' ? payload.exp : null
  if (exp == null) return false
  return Date.now() >= exp * 1000
}
