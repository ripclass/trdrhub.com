import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getAuth0Client } from '@/lib/auth0'

export default function AuthCallback() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string>('Processing authentication...')

  useEffect(() => {
    const processCallback = async () => {
      try {
        setStatus('Completing authentication...')
        
        // Auth0 handles the callback - get the token
        const auth0 = await getAuth0Client()
        const isAuthenticated = await auth0.isAuthenticated()
        
        if (!isAuthenticated) {
          // Handle the callback
          await auth0.handleRedirectCallback()
        }

        // Get Auth0 access token
        const token = await auth0.getTokenSilently()
        if (!token) {
          throw new Error('No Auth0 token available')
        }

        setStatus('Authenticating with backend...')
        
        // Login to backend API with Auth0 token
        const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'
        const loginResponse = await fetch(`${API_BASE_URL}/auth/auth0`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          credentials: 'include',
          body: JSON.stringify({ token }),
        })
        
        if (!loginResponse.ok) {
          const errorData = await loginResponse.json().catch(() => ({ detail: 'Backend authentication failed' }))
          throw new Error(errorData.detail || 'Backend authentication failed')
        }
        
        const tokenData = await loginResponse.json()
        if (tokenData.access_token) {
          // Store backend JWT token for admin API calls
          localStorage.setItem('trdrhub_api_token', tokenData.access_token)
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
            
            // Otherwise redirect to appropriate dashboard based on role
            const role = onboardingStatus.role
            const details = onboardingStatus.details || {}
            const businessTypes = Array.isArray(details.business_types) ? details.business_types : []
            const hasBoth = businessTypes.includes('exporter') && businessTypes.includes('importer')
            const companySize = details?.company?.size
            
            let destination = '/lcopilot/exporter-dashboard'
            if (role === 'bank_officer' || role === 'bank_admin') {
              destination = '/lcopilot/bank-dashboard'
            } else if (role === 'tenant_admin') {
              destination = '/lcopilot/enterprise-dashboard'
            } else if (hasBoth && companySize === 'sme') {
              destination = '/lcopilot/combined-dashboard'
            } else if (role === 'importer') {
              destination = '/lcopilot/importer-dashboard'
            }
            
            setStatus('Success! Redirecting...')
            setTimeout(() => {
              navigate(destination)
            }, 500)
            return
          }
        } catch (onboardingError) {
          console.warn('Failed to check onboarding status:', onboardingError)
        }
        
        // Fallback: redirect to dashboard
        setStatus('Success! Redirecting...')
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

