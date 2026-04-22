/**
 * Moment-aware importer action hooks.
 *
 * One hook per endpoint under /api/importer/*, written plain (no
 * @tanstack/react-query) so they compose the same way useValidate and
 * useResumeValidate do in this codebase. Each returns an imperative
 * callable plus {isLoading, error} state.
 *
 * Endpoints
 *   POST /api/importer/amendment-request   → PDF blob
 *   POST /api/importer/supplier-fix-pack   → signed-URL download info
 *   POST /api/importer/notify-supplier     → notification receipt
 *   POST /api/importer/bank-precheck       → tightened verdict + memo
 */

import { useCallback, useState } from "react";
import { api } from "@/api/client";

// ---------------------------------------------------------------------------
// Shared types
// ---------------------------------------------------------------------------

export interface ImporterActionError {
  message: string;
  statusCode?: number;
}

// ---------------------------------------------------------------------------
// Amendment request (Moment 1)
// ---------------------------------------------------------------------------

export interface AmendmentRequestVars {
  validationSessionId: string;
}

export const useAmendmentRequest = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ImporterActionError | null>(null);

  const mutateAsync = useCallback(async (vars: AmendmentRequestVars): Promise<Blob> => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await api.post(
        "/api/importer/amendment-request",
        { validation_session_id: vars.validationSessionId },
        { responseType: "blob" },
      );
      return response.data as Blob;
    } catch (err: any) {
      const e: ImporterActionError = {
        message: err?.response?.data?.detail || err?.message || "Amendment request failed",
        statusCode: err?.response?.status,
      };
      setError(e);
      throw e;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return { mutateAsync, isLoading, error };
};

// ---------------------------------------------------------------------------
// Supplier fix pack (Moment 2)
// ---------------------------------------------------------------------------

export interface SupplierFixPackVars {
  validationSessionId: string;
  lcNumber?: string;
}

export interface SupplierFixPackResult {
  download_url: string;
  file_name: string;
  generated_at: string;
  issue_count: number;
}

export const useSupplierFixPack = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ImporterActionError | null>(null);

  const mutateAsync = useCallback(
    async (vars: SupplierFixPackVars): Promise<SupplierFixPackResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.post<SupplierFixPackResult>(
          "/api/importer/supplier-fix-pack",
          {
            validation_session_id: vars.validationSessionId,
            lc_number: vars.lcNumber,
          },
        );
        return response.data;
      } catch (err: any) {
        const e: ImporterActionError = {
          message: err?.response?.data?.detail || err?.message || "Fix pack generation failed",
          statusCode: err?.response?.status,
        };
        setError(e);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutateAsync, isLoading, error };
};

// ---------------------------------------------------------------------------
// Notify supplier (Moment 2)
// ---------------------------------------------------------------------------

export interface NotifySupplierVars {
  validationSessionId: string;
  supplierEmail: string;
  message?: string;
  lcNumber?: string;
}

export interface NotifySupplierResult {
  success: boolean;
  message: string;
  notification_id: string;
  sent_at: string;
}

export const useNotifySupplier = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ImporterActionError | null>(null);

  const mutateAsync = useCallback(
    async (vars: NotifySupplierVars): Promise<NotifySupplierResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.post<NotifySupplierResult>(
          "/api/importer/notify-supplier",
          {
            validation_session_id: vars.validationSessionId,
            supplier_email: vars.supplierEmail,
            message: vars.message,
            lc_number: vars.lcNumber,
          },
        );
        return response.data;
      } catch (err: any) {
        const e: ImporterActionError = {
          message: err?.response?.data?.detail || err?.message || "Notify supplier failed",
          statusCode: err?.response?.status,
        };
        setError(e);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutateAsync, isLoading, error };
};

// ---------------------------------------------------------------------------
// Bank precheck (Moment 2)
// ---------------------------------------------------------------------------

export interface BankPrecheckVars {
  validationSessionId: string;
  lcNumber: string;
  bankName?: string;
  notes?: string;
}

export type PrecheckVerdict = "approve" | "review" | "reject";

export interface BankPrecheckResult {
  success: boolean;
  message: string;
  request_id: string;
  submitted_at: string;
  bank_name?: string | null;
  precheck_verdict?: PrecheckVerdict;
  counts?: { critical: number; major: number; minor: number; info?: number };
  memo?: string;
}

export const useBankPrecheck = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ImporterActionError | null>(null);

  const mutateAsync = useCallback(
    async (vars: BankPrecheckVars): Promise<BankPrecheckResult> => {
      setIsLoading(true);
      setError(null);
      try {
        const response = await api.post<BankPrecheckResult>(
          "/api/importer/bank-precheck",
          {
            validation_session_id: vars.validationSessionId,
            lc_number: vars.lcNumber,
            bank_name: vars.bankName,
            notes: vars.notes,
          },
        );
        return response.data;
      } catch (err: any) {
        const e: ImporterActionError = {
          message: err?.response?.data?.detail || err?.message || "Bank precheck failed",
          statusCode: err?.response?.status,
        };
        setError(e);
        throw e;
      } finally {
        setIsLoading(false);
      }
    },
    [],
  );

  return { mutateAsync, isLoading, error };
};
