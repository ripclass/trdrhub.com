import { useState, useCallback } from 'react';
import { api } from '@/api/client';

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

// Removed mock data - API calls should fail properly instead of using mock data

// Hook for managing LC versions
export const useVersions = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<VersionError | null>(null);

  const getVersions = useCallback(async (lcNumber: string): Promise<LCVersion[]> => {
    setIsLoading(true);
    setError(null);

    try {
      // Try real API first, fall back to mock
      const response = await api.get(`/api/lc/${lcNumber}/versions`);
      return response.data;
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
      const response = await api.get(`/api/lc/${lcNumber}/check`);
      return response.data;
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
      const response = await api.get('/api/lc/amended');
      return response.data;
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
      const response = await api.get(`/api/lc/${lcNumber}/compare`, {
        params: { from: fromVersion, to: toVersion }
      });
      return response.data;
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