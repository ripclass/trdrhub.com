import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './hooks/use-auth'
import { AdminAuthProvider } from './lib/admin/auth'
import { OnboardingProvider } from './components/onboarding/OnboardingProvider'
import App from './App.tsx'
import './index.css'
import { Toaster } from './components/ui/toaster'
import ErrorBoundary from './components/app/ErrorBoundary'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      cacheTime: 10 * 60 * 1000, // 10 minutes
      retry: 2,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
  },
})

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <OnboardingProvider>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <AdminAuthProvider>
              <ErrorBoundary>
                <App />
              </ErrorBoundary>
              <Toaster />
            </AdminAuthProvider>
          </BrowserRouter>
        </QueryClientProvider>
      </OnboardingProvider>
    </AuthProvider>
  </React.StrictMode>,
)
