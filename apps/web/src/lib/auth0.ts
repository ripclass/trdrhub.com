import { createAuth0Client, Auth0Client } from '@auth0/auth0-spa-js'

let auth0Client: Auth0Client | null = null

export async function getAuth0Client(): Promise<Auth0Client> {
  if (auth0Client) {
    return auth0Client
  }

  const domain = import.meta.env.VITE_AUTH0_DOMAIN
  const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID
  const redirectUri = typeof window !== 'undefined' ? `${window.location.origin}/auth/callback` : undefined

  if (!domain || !clientId) {
    throw new Error('Auth0 domain and client ID must be configured. Set VITE_AUTH0_DOMAIN and VITE_AUTH0_CLIENT_ID environment variables.')
  }

  auth0Client = await createAuth0Client({
    domain,
    clientId,
    authorizationParams: {
      redirect_uri: redirectUri,
      audience: import.meta.env.VITE_AUTH0_AUDIENCE, // Optional: API identifier
    },
  })

  return auth0Client
}

