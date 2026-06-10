/** @type {import('next').NextConfig} */
// The payment page calls the backend API directly (e.g. to fetch the order),
// so the backend origin must be allowed in connect-src or the browser's CSP
// blocks the fetch. Allow the configured backend plus localhost for dev.
const backendBaseUrl =
  process.env.NEXT_PUBLIC_BACKEND_BASE_URL || process.env.BACKEND_BASE_URL || 'http://localhost:8000'
const backendOrigins = new Set([backendBaseUrl])
try {
  // Add both 127.0.0.1 and localhost variants so dev works regardless of which the browser uses.
  const { protocol, port } = new URL(backendBaseUrl)
  const portSuffix = port ? `:${port}` : ''
  backendOrigins.add(`${protocol}//localhost${portSuffix}`)
  backendOrigins.add(`${protocol}//127.0.0.1${portSuffix}`)
} catch {}
const connectSrc = ["'self'", 'https://checkout.postfinance.ch', ...backendOrigins].join(' ')

const postFinanceCsp =
  `script-src 'self' 'unsafe-inline' https://checkout.postfinance.ch; frame-src 'self' https://checkout.postfinance.ch; connect-src ${connectSrc}`

const nextConfig = {
  reactStrictMode: true,
  images: {
    domains: ['127.0.0.1', 'localhost'],
    remotePatterns: [
      { protocol: 'http', hostname: '127.0.0.1' },
      { protocol: 'http', hostname: 'localhost' },
    ],
  },
  output: 'standalone',
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
};

module.exports = nextConfig
