/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_SUPABASE_URL: string
  readonly VITE_SUPABASE_ANON_KEY: string
  readonly VITE_SUPABASE_PROJECT_REF: string
  readonly VITE_GUEST_MODE?: string
  readonly VITE_STRIPE_PRICE_STARTER?: string
  readonly VITE_STRIPE_PRICE_PROFESSIONAL?: string
  readonly VITE_STRIPE_PRICE_ENTERPRISE?: string
  readonly VITE_STRIPE_TAX_ENABLED?: string
  readonly VITE_BILLING_PROVIDERS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
