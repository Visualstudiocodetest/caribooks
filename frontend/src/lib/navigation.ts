/**
 * Sanitize a `returnTo` query value before handing it to router.push/replace.
 *
 * Only same-origin relative paths are allowed. Anything that could redirect the
 * user off-site — an absolute URL (`https://evil.com`), a protocol-relative URL
 * (`//evil.com`), or a `javascript:`/backslash trick — is rejected and replaced
 * with `fallback`. This closes the open-redirect on the login/register pages.
 */
export function safeReturnTo(value: string | null | undefined, fallback = '/'): string {
  if (!value) return fallback
  // Must be a root-relative path…
  if (!value.startsWith('/')) return fallback
  // …but not protocol-relative ("//host") or a backslash variant ("/\\host").
  if (value.startsWith('//') || value.startsWith('/\\')) return fallback
  // Reject control chars / whitespace that could be used to smuggle a scheme.
  if (/[\x00-\x1f\s]/.test(value)) return fallback
  return value
}
