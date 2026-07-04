import { useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import { apiClient } from '../api/client'

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: Record<string, unknown>) => void
          renderButton: (el: HTMLElement, options: Record<string, unknown>) => void
        }
      }
    }
  }
}

const CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

export function LoginButton() {
  const { login } = useAuth()
  const buttonRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!CLIENT_ID) return
    let cancelled = false

    const tryInit = () => {
      if (cancelled) return
      if (!window.google?.accounts?.id || !buttonRef.current) {
        setTimeout(tryInit, 100)
        return
      }
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback: async (response: { credential: string }) => {
          try {
            const user = await apiClient.loginWithGoogle(response.credential)
            login(user)
          } catch (err) {
            console.error('Google login failed', err)
          }
        },
      })
      window.google.accounts.id.renderButton(buttonRef.current, {
        theme: 'filled_black',
        size: 'medium',
        shape: 'pill',
        text: 'signin_with',
      })
    }

    tryInit()
    return () => { cancelled = true }
  }, [login])

  if (!CLIENT_ID) {
    return <p className="text-[10px] text-zinc-600">Google sign-in not configured</p>
  }

  return <div ref={buttonRef} />
}
