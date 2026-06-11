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
        source: '/payment',
        headers: [{ key: 'Content-Security-Policy', value: postFinanceCsp }],
      },
      {
        source: '/payment/:path*',
        headers: [{ key: 'Content-Security-Policy', value: postFinanceCsp }],
      },
    ]
  },
}

module.exports = nextConfig
