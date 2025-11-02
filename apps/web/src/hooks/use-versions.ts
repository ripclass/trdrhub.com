import { useState, useCallback } from 'react';
import axios from 'axios';
import { supabase } from '@/lib/supabase';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

// Add request interceptor to automatically include auth token
api.interceptors.request.use(async (config) => {
  try {
    const {
      data: { session },
    } = await supabase.auth.getSession();
    if (session?.access_token) {
      config.headers = config.headers ?? {};
      config.headers.Authorization = `Bearer ${session.access_token}`;
    }
  } catch (error) {
    console.error('Failed to get auth token:', error);
  }
  return config;
});

export interface LCVersion {
  id: string;
  lc_number: string;
  version: string; // "V1", "V2", etc.
  uploaded_by: string;
  created_at: string;
  status: 'created' | 'processing' | 'completed' | 'failed';
  job_id: string;
  file_metadata: {
    files: Array<{
      name: string;
      size: number;
      type: string;
      document_type?: string;
    }>;
    total_files: number;
    total_size: number;
  };
  validation_results?: any;
  discrepancies?: any[];
}

export interface VersionComparison {
  lc_number: string;
  from_version: string;
  to_version: string;
  changes: {
    added_discrepancies: any[];
    removed_discrepancies: any[];
    modified_discrepancies: any[];
    status_change?: {
      from: string;
      to: string;
    };
  };
  summary: {
    total_changes: number;
    improvement_score: number; // -1 to 1, where 1 = much better
  };
}

export interface VersionError {
  message: string;
  type: 'network' | 'server' | 'validation' | 'unknown';
  statusCode?: number;
}

// Mock data for development
const mockVersions: Record<string, LCVersion[]> = {
  'BD-2024-001': [
    {
      id: 'version-1',
      lc_number: 'BD-2024-001',
      version: 'V1',
      uploaded_by: 'user@example.com',
      created_at: '2024-01-15T10:00:00Z',
      status: 'completed',
      job_id: 'job-v1-123',
      file_metadata: {
        files: [
          { name: 'LC_Original.pdf', size: 1024000, type: 'application/pdf', document_type: 'lc' },
          { name: 'Invoice_V1.pdf', size: 512000, type: 'application/pdf', document_type: 'invoice' }
        ],
        total_files: 2,
        total_size: 1536000
      },
      discrepancies: [
        {
          id: '1',
          severity: 'high',
          title: 'Amount Mismatch',
          description: 'Invoice amount exceeds LC amount'
        },
        {
          id: '2',
          severity: 'medium',
          title: 'Date Discrepancy',
          description: 'Shipment date is after LC expiry'
        }
      ]
    },
    {
      id: 'version-2',
      lc_number: 'BD-2024-001',
      version: 'V2',
      uploaded_by: 'user@example.com',
      created_at: '2024-01-16T14:30:00Z',
      status: 'completed',
      job_id: 'job-v2-456',
      file_metadata: {
        files: [
          { name: 'LC_Amended.pdf', size: 1024000, type: 'application/pdf', document_type: 'lc' },
          { name: 'Invoice_V2.pdf', size: 512000, type: 'application/pdf', document_type: 'invoice' },
          { name: 'Additional_Docs.pdf', size: 256000, type: 'application/pdf', document_type: 'other' }
        ],
        total_files: 3,
        total_size: 1792000
      },
      discrepancies: [
        {
          id: '2',
          severity: 'medium',
          title: 'Date Discrepancy',
          description: 'Shipment date is after LC expiry'
        }
      ]
    }
  ]
};

// Hook for managing LC versions
export const useVersions = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<VersionError | null>(null);

  const getVersions = useCallback(async (lcNumber: string): Promise<LCVersion[]> => {
    setIsLoading(true);
    setError(null);

    try {
      // Try real API first, fall back to mock
      try {
        const response = await api.get(`/api/lc/${lcNumber}/versions`);
        return response.data;
      } catch (apiError) {
        console.log('API unavailable, using mock versions');
        // Return mock data
        return mockVersions[lcNumber] || [];
      }
    } catch (err: any) {
      const versionError: VersionError = {
        type: 'unknown',
        message: err.message || 'Failed to fetch versions',
      };
      setError(versionError);
      throw versionError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const checkLCExists = useCallback(async (lcNumber: string): Promise<{ exists: boolean; nextVersion: string; currentVersions: number }> => {
    setIsLoading(true);
    setError(null);

    try {
      try {
        const response = await api.get(`/api/lc/${lcNumber}/check`);
        return response.data;
      } catch (apiError) {
        console.log('API unavailable, using mock check');
        // Mock check
        const versions = mockVersions[lcNumber] || [];
        return {
          exists: versions.length > 0,
          nextVersion: `V${versions.length + 1}`,
          currentVersions: versions.length
        };
      }
    } catch (err: any) {
      const versionError: VersionError = {
        type: 'unknown',
        message: err.message || 'Failed to check LC',
      };
      setError(versionError);
      throw versionError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getAllAmendedLCs = useCallback(async (): Promise<Array<{ lc_number: string; versions: number; latest_version: string; last_updated: string }>> => {
    setIsLoading(true);
    setError(null);

    try {
      try {
        const response = await api.get('/api/lc/amended');
        return response.data;
      } catch (apiError) {
        console.log('API unavailable, using mock amended LCs');
        // Mock data for amended LCs
        return Object.entries(mockVersions)
          .filter(([, versions]) => versions.length > 1)
          .map(([lcNumber, versions]) => ({
            lc_number: lcNumber,
            versions: versions.length,
            latest_version: versions[versions.length - 1].version,
            last_updated: versions[versions.length - 1].created_at
          }));
      }
    } catch (err: any) {
      const versionError: VersionError = {
        type: 'unknown',
        message: err.message || 'Failed to fetch amended LCs',
      };
      setError(versionError);
      throw versionError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    getVersions,
    checkLCExists,
    getAllAmendedLCs,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};

// Hook for comparing versions
export const useCompare = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<VersionError | null>(null);

  const compareVersions = useCallback(async (
    lcNumber: string,
    fromVersion: string,
    toVersion: string
  ): Promise<VersionComparison> => {
    setIsLoading(true);
    setError(null);

    try {
      try {
        const response = await api.get(`/api/lc/${lcNumber}/compare`, {
          params: { from: fromVersion, to: toVersion }
        });
        return response.data;
      } catch (apiError) {
        console.log('API unavailable, using mock comparison');

        // Mock comparison logic
        const versions = mockVersions[lcNumber] || [];
        const fromV = versions.find(v => v.version === fromVersion);
        const toV = versions.find(v => v.version === toVersion);

        if (!fromV || !toV) {
          throw new Error('Version not found');
        }

        const fromDiscrepancies = fromV.discrepancies || [];
        const toDiscrepancies = toV.discrepancies || [];

        const addedDiscrepancies = toDiscrepancies.filter(
          to => !fromDiscrepancies.find(from => from.id === to.id)
        );

        const removedDiscrepancies = fromDiscrepancies.filter(
          from => !toDiscrepancies.find(to => to.id === from.id)
        );

        const modifiedDiscrepancies = toDiscrepancies.filter(to => {
          const corresponding = fromDiscrepancies.find(from => from.id === to.id);
          return corresponding && JSON.stringify(corresponding) !== JSON.stringify(to);
        });

        const totalChanges = addedDiscrepancies.length + removedDiscrepancies.length + modifiedDiscrepancies.length;
        const improvementScore = removedDiscrepancies.length > addedDiscrepancies.length ? 0.5 : -0.2;

        return {
          lc_number: lcNumber,
          from_version: fromVersion,
          to_version: toVersion,
          changes: {
            added_discrepancies: addedDiscrepancies,
            removed_discrepancies: removedDiscrepancies,
            modified_discrepancies: modifiedDiscrepancies,
          },
          summary: {
            total_changes: totalChanges,
            improvement_score: improvementScore
          }
        };
      }
    } catch (err: any) {
      const versionError: VersionError = {
        type: 'unknown',
        message: err.message || 'Failed to compare versions',
      };
      setError(versionError);
      throw versionError;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    compareVersions,
    isLoading,
    error,
    clearError: () => setError(null),
  };
};