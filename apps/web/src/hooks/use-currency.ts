/**
 * useCurrency Hook
 * 
 * Returns the current user's preferred currency based on their
 * company's country setting (captured at registration).
 * 
 * Falls back to USD for unauthenticated users or missing data.
 */

import { useState, useEffect } from 'react';
import { useAuth } from './use-auth';
import { getCurrencyFromCountry, type CurrencyCode, CURRENCIES } from '@/lib/pricing';

interface UseCurrencyReturn {
  currency: CurrencyCode;
  currencySymbol: string;
  currencyName: string;
  isLoading: boolean;
  // For display
  formatPrice: (amount: number) => string;
}

// API base URL
const API_BASE = import.meta.env.VITE_API_URL || 'https://trdrhub-api.onrender.com';

export function useCurrency(): UseCurrencyReturn {
  const { user, isLoading: authLoading } = useAuth();
  const [currency, setCurrency] = useState<CurrencyCode>('USD');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchCompanyCurrency() {
      if (authLoading) return;
      
      if (!user) {
        // Try to detect from IP for unauthenticated users
        try {
          const geoRes = await fetch('/api/geo');
          const geoData = await geoRes.json();
          if (geoData.country) {
            setCurrency(getCurrencyFromCountry(geoData.country));
          }
        } catch {
          // Fall back to USD
          setCurrency('USD');
        }
        setIsLoading(false);
        return;
      }

      // Fetch company info to get currency
      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          credentials: 'include',
        });
        
        if (response.ok) {
          const data = await response.json();
          // Try to get currency from company data
          if (data.company?.currency) {
            setCurrency(data.company.currency as CurrencyCode);
          } else if (data.company?.country) {
            setCurrency(getCurrencyFromCountry(data.company.country));
          }
        }
      } catch (err) {
        console.warn('Failed to fetch company currency:', err);
      }
      
      setIsLoading(false);
    }

    fetchCompanyCurrency();
  }, [user, authLoading]);

  const currencyInfo = CURRENCIES[currency] || CURRENCIES.USD;

  const formatPrice = (amount: number): string => {
    const formattedAmount = amount.toLocaleString();
    if (currencyInfo.position === 'after') {
      return `${formattedAmount} ${currencyInfo.symbol}`;
    }
    return `${currencyInfo.symbol}${formattedAmount}`;
  };

  return {
    currency,
    currencySymbol: currencyInfo.symbol,
    currencyName: currencyInfo.name,
    isLoading: isLoading || authLoading,
    formatPrice,
  };
}

// Simple hook for just getting the symbol (for quick displays)
export function useCurrencySymbol(): string {
  const { currencySymbol } = useCurrency();
  return currencySymbol;
}

