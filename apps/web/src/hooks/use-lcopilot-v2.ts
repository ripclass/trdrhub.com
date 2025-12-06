/**
 * V2 LCopilot Hook
 * 
 * Hook for using the V2 validation pipeline.
 */

import { useState, useCallback } from 'react';
import { useToast } from '@/hooks/use-toast';
import type { ValidationResultsV2Data } from '@/components/v2/ValidationResultsV2';

interface V2ValidationOptions {
  lcNumber?: string;
  userType?: 'exporter' | 'importer' | 'bank';
  strictMode?: boolean;
}

interface UseLCopilotV2Result {
  validate: (files: File[], options?: V2ValidationOptions) => Promise<ValidationResultsV2Data>;
  isLoading: boolean;
  error: string | null;
  results: ValidationResultsV2Data | null;
  reset: () => void;
}

const API_BASE = import.meta.env.VITE_API_URL || '';

export function useLCopilotV2(): UseLCopilotV2Result {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ValidationResultsV2Data | null>(null);
  const { toast } = useToast();
  
  const validate = useCallback(async (
    files: File[],
    options: V2ValidationOptions = {},
  ): Promise<ValidationResultsV2Data> => {
    setIsLoading(true);
    setError(null);
    
    try {
      // Build form data
      const formData = new FormData();
      
      // Add files
      files.forEach((file) => {
        formData.append('files', file);
      });
      
      // Add options
      if (options.lcNumber) {
        formData.append('lc_number', options.lcNumber);
      }
      if (options.userType) {
        formData.append('user_type', options.userType);
      }
      if (options.strictMode !== undefined) {
        formData.append('strict_mode', String(options.strictMode));
      }
      
      // Call V2 API
      const response = await fetch(`${API_BASE}/api/v2/validate`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Validation failed: ${response.status}`);
      }
      
      const data: ValidationResultsV2Data = await response.json();
      
      setResults(data);
      
      // Show toast based on verdict
      if (data.verdict.status === 'SUBMIT') {
        toast({
          title: 'Validation Complete',
          description: 'Documents are ready to submit to the bank.',
        });
      } else if (data.verdict.status === 'REJECT') {
        toast({
          title: 'Issues Found',
          description: `${data.issues.length} discrepancies need attention.`,
          variant: 'destructive',
        });
      } else {
        toast({
          title: 'Validation Complete',
          description: data.verdict.message,
        });
      }
      
      return data;
      
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Validation failed';
      setError(message);
      toast({
        title: 'Validation Error',
        description: message,
        variant: 'destructive',
      });
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [toast]);
  
  const reset = useCallback(() => {
    setResults(null);
    setError(null);
    setIsLoading(false);
  }, []);
  
  return {
    validate,
    isLoading,
    error,
    results,
    reset,
  };
}

/**
 * Check V2 pipeline health
 */
export async function checkV2Health(): Promise<{
  status: string;
  features: Record<string, boolean>;
  canEnsemble: boolean;
  providers: string[];
}> {
  const response = await fetch(`${API_BASE}/api/v2/health`);
  if (!response.ok) {
    throw new Error('V2 pipeline health check failed');
  }
  return response.json();
}

/**
 * List available AI providers
 */
export async function listV2Providers(): Promise<{
  providers: Array<{
    name: string;
    id: string;
    model: string;
    available: boolean;
    bestFor: string[];
  }>;
  ensembleAvailable: boolean;
}> {
  const response = await fetch(`${API_BASE}/api/v2/providers`);
  if (!response.ok) {
    throw new Error('Failed to list V2 providers');
  }
  return response.json();
}

