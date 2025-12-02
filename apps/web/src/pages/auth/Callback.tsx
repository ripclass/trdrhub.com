import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '@/lib/supabase'
import { getOnboardingStatus } from '@/api/onboarding'

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

        // Login to backend API to get JWT token for admin endpoints
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
          const loginResponse = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include',
            body: JSON.stringify({
              email: currentSession.user.email,
              password: '', // Not needed for Supabase token auth
            }),
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

        setStatus('Checking onboarding status...')
        
        // Check onboarding status and redirect accordingly
        try {
          const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
          const onboardingResponse = await fetch(`${API_BASE_URL}/onboarding/status`, {
            method: 'GET',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('trdrhub_api_token') || ''}`,
            },
            credentials: 'include',
          })
          
          if (onboardingResponse.ok) {
            const onboardingStatus = await onboardingResponse.json()
            
            // If onboarding is not complete, redirect to onboarding page
            if (!onboardingStatus.completed) {
              setStatus('Redirecting to onboarding...')
              setTimeout(() => {
                navigate('/onboarding')
              }, 500)
              return
            }
            
            // Simplified routing: Banks go to bank dashboard, everyone else to Hub
            const role = onboardingStatus.role
            const destination = (role === 'bank_officer' || role === 'bank_admin')
              ? '/lcopilot/bank-dashboard'
              : '/hub'
            
            setStatus('Success! Redirecting...')
            setTimeout(() => {
              navigate(destination)
            }, 500)
            return
          }
        } catch (onboardingError) {
          console.warn('Failed to check onboarding status:', onboardingError)
        }
        
        // Fallback: redirect to Hub
        setStatus('Success! Redirecting...')
        setTimeout(() => {
          navigate('/hub')
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
