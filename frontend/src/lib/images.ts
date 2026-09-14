/**
 * True when `src` is an absolute http(s) URL rather than a path served by this
 * Next.js app itself (e.g. a /public asset like "/logo-caritas.jpg"). Used to
 * decide when to pass `unoptimized` to next/image.
 *
 * This used to also treat an absolute URL as "internal" (safe to run through
 * Next's Image Optimizer) whenever its path contained `/static/images/` —
 * on the theory that those covers are "our own". But every `image_link` the
 * API returns for a self-hosted cover is a *fully-qualified* URL to the
 * backend's own origin (see backend/presentation/images_router.py's
 * `fetch_image`, which always returns `request.base_url + path`), which is a
 * different origin than this Next.js app in every environment except local
 * dev (where the backend happens to run on localhost/127.0.0.1, both
 * allow-listed in next.config.js's `images.remotePatterns`). In production
 * the backend's real domain is not on that list, so Next's optimizer
 * silently refused to fetch it and the cover never rendered — while the
 * admin book list, which hardcodes `unoptimized` unconditionally, worked
 * fine. Any absolute URL must be treated as external.
 */
export function isExternalImage(src: string | null | undefined): boolean {
  return Boolean(src && src.startsWith('http'))
}
