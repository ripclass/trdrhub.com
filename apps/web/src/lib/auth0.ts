import { createAuth0Client, type Auth0Client } from '@auth0/auth0-spa-js'

let auth0Client: Auth0Client | null = null

const AUTH0_DOMAIN = import.meta.env.VITE_AUTH0_DOMAIN || 'dev-2zhljb8cf2kc2h5t.us.auth0.com'
const AUTH0_CLIENT_ID = import.meta.env.VITE_AUTH0_CLIENT_ID || ''
const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE || ''

export async function getAuth0Client(): Promise<Auth0Client> {
  if (auth0Client) {
    return auth0Client
  }

  auth0Client = await createAuth0Client({
    domain: AUTH0_DOMAIN,
    clientId: AUTH0_CLIENT_ID,
    authorizationParams: {
      redirect_uri: typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined,
      audience: AUTH0_AUDIENCE || undefined,
    },
    cacheLocation: 'localstorage',
  })

  return auth0Client
}

export async function handleAuth0Callback(): Promise<string | null> {
  const client = await getAuth0Client()
  const query = window.location.search
  
  if (query.includes('code=') && query.includes('state=')) {
    try {
      await client.handleRedirectCallback()
      const token = await client.getTokenSilently()
      return token || null
    } catch (error) {
      console.error('Auth0 callback error:', error)
      return null
    }
  }
  
  return null
}

export async function getAuth0Token(): Promise<string | null> {
  try {
    const client = await getAuth0Client()
    const isAuthenticated = await client.isAuthenticated()
    
    if (isAuthenticated) {
      const token = await client.getTokenSilently()
      return token || null
    }
    
    return null
  } catch (error) {
    console.error('Error getting Auth0 token:', error)
    return null
  }
}

export async function logoutAuth0(): Promise<void> {
  const client = await getAuth0Client()
  await client.logout({
    logoutParams: {
      returnTo: typeof window !== 'undefined' ? window.location.origin : undefined,
    },
  })
}

