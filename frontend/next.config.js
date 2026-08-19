/** @type {import('next').NextConfig} */
const backendBaseUrl =
  process.env.BACKEND_BASE_URL || process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000'

// 'self' already covers /api/proxy requests. Keep the backend origin in
// connect-src so PostFinance redirect pages that call the backend directly
// (no proxy needed) still work.
const backendOrigins = new Set([backendBaseUrl])
try {
  const { protocol, port } = new URL(backendBaseUrl)
  const portSuffix = port ? `:${port}` : ''
  backendOrigins.add(`${protocol}//localhost${portSuffix}`)
  backendOrigins.add(`${protocol}//127.0.0.1${portSuffix}`)
} catch {}
const connectSrc = ["'self'", 'https://checkout.postfinance.ch', 'https://oauth2.googleapis.com', ...backendOrigins].join(' ')

// One CSP/COOP pair for the whole app. This used to be split — a strict
// baseline everywhere plus a more permissive PostFinance policy scoped to
// /payment — but CSP and COOP are headers tied to the *document* that was
// served, not the route currently shown. /payment is reached via
// router.push (see useCreateOrder.ts), a client-side navigation that never
// re-fetches the document, so the browser kept enforcing the *previous*
// page's (stricter) policy: Google Identity Services' stylesheet and the
// PostFinance iframe script would both get blocked, only working after a
// hard refresh actually re-requested /payment. A single policy permissive
// enough for both integrations, applied everywhere, makes that ambiguity
// irrelevant. 'unsafe-inline'/'unsafe-eval' are required by Next.js's inline
// styles/runtime; the rest is locked down.
const googleOrigins = 'https://accounts.google.com https://apis.google.com'
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${googleOrigins} https://checkout.postfinance.ch`,
  `style-src 'self' 'unsafe-inline' https://accounts.google.com`,
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  `connect-src ${connectSrc}`,
  `frame-src 'self' ${googleOrigins} https://checkout.postfinance.ch`,
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'self'",
].join('; ')

const nextConfig = {
  reactStrictMode: true,
  images: {
    remotePatterns: [
      { protocol: 'http',  hostname: '127.0.0.1' },
      { protocol: 'http',  hostname: 'localhost' },
      { protocol: 'https', hostname: 'covers.openlibrary.org' },
      { protocol: 'https', hostname: 'books.google.com' },
      { protocol: 'https', hostname: '*.googleusercontent.com' },
    ],
  },
  output: 'standalone',
  // Proxy all /api/proxy/* requests to the backend.
  // Browser requests stay on the same Vercel origin → no CORS needed.
  // Server Components bypass this and call backendBaseUrl directly.
  async rewrites() {
    return [
      {
        source: '/api/proxy/:path*',
        destination: `${backendBaseUrl}/:path*`,
      },
    ]
  },
  async headers() {
    return [
      {
        // Same policy on every route (see the comment above `csp`) — COOP is
        // 'unsafe-none' everywhere too, for the same document-vs-route reason:
        // the PostFinance iframe on /payment needs cross-origin postMessage,
        // and that has to already be in effect before the SPA navigates there.
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: csp },
          { key: 'Cross-Origin-Opener-Policy', value: 'unsafe-none' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
