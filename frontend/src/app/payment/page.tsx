import { Suspense } from 'react'
import { PaymentClient } from './PaymentClient'

export const dynamic = 'force-dynamic'

export default function PaymentPage() {
  return (
    <Suspense fallback={<div className="muted">Chargement…</div>}>
      <PaymentClient />
    </Suspense>
  )
}
