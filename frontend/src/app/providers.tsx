'use client'

import { AuthProvider } from '@/components/auth/AuthProvider'
import { CartProvider } from '@/components/cart/CartProvider'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'
import type { ReactNode } from 'react'

export function Providers({ children }: { children: ReactNode }) {
  // One QueryClient per browser session (created lazily so it isn't shared across
  // requests during SSR). Data fetching for client components now goes through
  // React Query — cache + dedup + retry — per the project data-fetching standard.
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  )

  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <CartProvider>{children}</CartProvider>
      </AuthProvider>
    </QueryClientProvider>
  )
}
