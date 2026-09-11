'use client'

import { useEffect, useRef } from 'react'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string
            callback: (response: { credential: string }) => void
            auto_select?: boolean
          }) => void
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: 'outline' | 'filled_blue' | 'filled_black'
              size?: 'large' | 'medium' | 'small'
              width?: number
              text?: 'signin_with' | 'signup_with' | 'continue_with'
              shape?: 'rectangular' | 'pill' | 'circle' | 'square'
              locale?: string
            }
          ) => void
          cancel: () => void
        }
      }
    }
  }
}

type Props = {
  onCredential: (credential: string) => void
  text?: 'signin_with' | 'signup_with' | 'continue_with'
}

export function GoogleSignInButton({ onCredential, text = 'signin_with' }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? ''

  useEffect(() => {
    if (!clientId) return

    function init() {
      if (!window.google || !containerRef.current) return
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => onCredential(response.credential),
        auto_select: false,
      })
      window.google.accounts.id.renderButton(containerRef.current, {
        theme: 'outline',
        size: 'large',
        width: containerRef.current.offsetWidth || 360,
        text,
        shape: 'rectangular',
        locale: 'fr',
      })
    }

    if (window.google) {
      init()
      return
    }

    const existing = document.getElementById('gsi-script')
    if (!existing) {
      const script = document.createElement('script')
      script.id = 'gsi-script'
      script.src = 'https://accounts.google.com/gsi/client'
      script.async = true
      script.defer = true
      script.onload = init
      document.head.appendChild(script)
    } else {
      existing.addEventListener('load', init)
    }

    return () => {
      window.google?.accounts.id.cancel()
    }
  }, [clientId, onCredential, text])

  if (!clientId) return null

  return <div ref={containerRef} style={{ width: '100%' }} />
}
