/** @type {import('next').NextConfig} */
const backendBaseUrl =
  process.env.BACKEND_BASE_URL || process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000'

// CSP for the payment page only — 'self' already covers /api/proxy requests.
// Keep the backend origin in connect-src so PostFinance redirect pages that
// call the backend directly (no proxy needed) still work.
const backendOrigins = new Set([backendBaseUrl])
try {
  const { protocol, port } = new URL(backendBaseUrl)
  const portSuffix = port ? `:${port}` : ''
  backendOrigins.add(`${protocol}//localhost${portSuffix}`)
  backendOrigins.add(`${protocol}//127.0.0.1${portSuffix}`)
} catch {}
const connectSrc = ["'self'", 'https://checkout.postfinance.ch', 'https://oauth2.googleapis.com', ...backendOrigins].join(' ')

const postFinanceCsp =
  `script-src 'self' 'unsafe-inline' https://checkout.postfinance.ch; frame-src 'self' https://checkout.postfinance.ch; connect-src ${connectSrc}`

// App-wide baseline CSP for every route EXCEPT /payment (which needs the more
// permissive PostFinance policy above). Previously only /payment had any CSP, so
// the rest of the app had none — which, combined with the localStorage token,
// magnified XSS impact. 'unsafe-inline'/'unsafe-eval' are required by Next.js's
// inline styles/runtime; the rest is locked down.
const googleOrigins = 'https://accounts.google.com https://apis.google.com'
const baselineCsp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline' 'unsafe-eval' ${googleOrigins}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: https:",
  "font-src 'self' data:",
  `connect-src ${connectSrc}`,
  `frame-src 'self' ${googleOrigins}`,
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
        // Baseline security headers for every route except /payment (which has its
        // own PostFinance-specific CSP below — applying both would send two CSP
        // headers and the browser would enforce the intersection, breaking the
        // PostFinance iframe). Negative lookahead excludes /payment and /payment/*.
        source: '/((?!payment).*)',
        headers: [
          { key: 'Content-Security-Policy', value: baselineCsp },
          { key: 'Cross-Origin-Opener-Policy', value: 'same-origin-allow-popups' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Frame-Options', value: 'SAMEORIGIN' },
        ],
      },
      {
        // PostFinance iframe communicates via postMessage — COOP must be unsafe-none
        // to allow cross-origin iframes (not just popups) to reach the parent window.
        source: '/payment',
        headers: [
          { key: 'Content-Security-Policy', value: postFinanceCsp },
          { key: 'Cross-Origin-Opener-Policy', value: 'unsafe-none' },
        ],
      },
      {
        source: '/payment/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: postFinanceCsp },
          { key: 'Cross-Origin-Opener-Policy', value: 'unsafe-none' },
        ],
      },
    ]
  },
}

module.exports = nextConfig
