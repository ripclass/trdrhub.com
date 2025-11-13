import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('Processing authentication...')

  useEffect(() => {
    const processCallback = async () => {
      try {
        setStatus('Completing authentication...')
        
        // Supabase handles the OAuth callback automatically
        // Check if we have a session
        const { data: { session }, error: sessionError } = await supabase.auth.getSession()
        
        if (sessionError) {
          throw sessionError
        }
        
        if (!session) {
          // Wait a bit for Supabase to process the callback
          await new Promise(resolve => setTimeout(resolve, 1000))
          const { data: { session: retrySession } } = await supabase.auth.getSession()
          
          if (!retrySession) {
            throw new Error('No session found after callback')
          }
        }

        setStatus('Authenticating with backend...')
        
        // Get Supabase token and send to backend for JWT token
        const currentSession = session || (await supabase.auth.getSession()).data.session
        if (!currentSession?.access_token) {
          throw new Error('No access token available')
        }

        // Also login to backend API to get JWT token for admin endpoints
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
          const loginResponse = await fetch(`${API_BASE_URL}/auth/auth0`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({ token: currentSession.access_token }),
          })
          
          if (loginResponse.ok) {
            const tokenData = await loginResponse.json()
            if (tokenData.access_token) {
              // Store backend JWT token for admin API calls
              localStorage.setItem('trdrhub_api_token', tokenData.access_token)
            }
          }
        } catch (backendLoginError) {
          // Non-critical - Supabase login succeeded, backend login is optional
          console.warn('Backend login failed (non-critical):', backendLoginError)
        }

        setStatus('Success! Redirecting...')
        
        // Redirect to dashboard
        setTimeout(() => {
          navigate('/dashboard')
        }, 500)
      } catch (err) {
        console.error('Auth callback error:', err)
        setError(err instanceof Error ? err.message : 'Authentication failed')
        setTimeout(() => {
          navigate('/login')
        }, 3000)
      }
    }

    processCallback()
  }, [navigate])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <div className="mb-4">
          {error ? (
            <div className="text-red-600">
              <h2 className="text-xl font-semibold">Authentication Failed</h2>
              <p className="mt-2">{error}</p>
              <p className="mt-4 text-sm">Redirecting to login...</p>
            </div>
          ) : (
            <div>
              <div className="mb-4 inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-current border-r-transparent"></div>
              <p className="text-lg">{status}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

