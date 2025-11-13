import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { handleAuth0Callback, getAuth0Token } from '@/lib/auth0'
import { api } from '@/api/client'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('Processing authentication...')

  useEffect(() => {
    const processCallback = async () => {
      try {
        setStatus('Exchanging authorization code...')
        
        // Handle Auth0 callback and get token
        const auth0Token = await handleAuth0Callback()
        
        if (!auth0Token) {
          // Check if this is a Supabase callback (Google OAuth)
          const urlParams = new URLSearchParams(window.location.search)
          const code = urlParams.get('code')
          
          if (code) {
            // This might be a Supabase callback - let Supabase handle it
            setStatus('Redirecting...')
            navigate('/dashboard')
            return
          }
          
          throw new Error('No authorization code found')
        }

        setStatus('Authenticating with backend...')
        
        // Send Auth0 token to backend for validation and user creation
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const response = await fetch(`${API_BASE_URL}/auth/auth0`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ token: auth0Token }),
        })

        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: 'Authentication failed' }))
          throw new Error(errorData.detail || 'Authentication failed')
        }

        const data = await response.json()
        
        // Store backend JWT token
        if (data.access_token) {
          localStorage.setItem('trdrhub_api_token', data.access_token)
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

