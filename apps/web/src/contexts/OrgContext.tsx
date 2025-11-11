/**
 * Bank Org Context
 * Manages active organization selection for multi-org switching
 */
import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { bankOrgsApi, BankOrg as APIBankOrg } from "@/api/bank";

export interface BankOrg {
  id: string;
  name: string;
  code?: string;
  kind: "group" | "region" | "branch";
  path: string;
}

interface OrgContextValue {
  activeOrgId: string | null;
  setActiveOrg: (orgId: string | null) => void;
  orgs: BankOrg[];
  isLoading: boolean;
  refreshOrgs: () => Promise<void>;
}

const OrgContext = createContext<OrgContextValue | undefined>(undefined);

export function useOrgContext(): OrgContextValue {
  const context = useContext(OrgContext);
  if (!context) {
    throw new Error("useOrgContext must be used within OrgProvider");
  }
  return context;
}

interface OrgProviderProps {
  children: React.ReactNode;
}

export function OrgProvider({ children }: OrgProviderProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [orgs, setOrgs] = useState<BankOrg[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  
  // Get active org from URL param or localStorage
  const activeOrgId = searchParams.get("org") || localStorage.getItem("bank_active_org") || null;
  
  // Persist org selection
  useEffect(() => {
    if (activeOrgId) {
      localStorage.setItem("bank_active_org", activeOrgId);
    } else {
      localStorage.removeItem("bank_active_org");
    }
  }, [activeOrgId]);
  
  // Fetch user's accessible orgs
  const fetchOrgs = useCallback(async () => {
    setIsLoading(true);
    try {
      const response = await bankOrgsApi.listOrgs();
      setOrgs(response.orgs);
    } catch (error) {
      console.error("Failed to fetch bank organizations:", error);
      setOrgs([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchOrgs();
  }, [fetchOrgs]);

  const refreshOrgs = fetchOrgs;

  const setActiveOrg = useCallback((orgId: string | null) => {
    const newParams = new URLSearchParams(searchParams);
    if (orgId) {
      newParams.set("org", orgId);
    } else {
      newParams.delete("org");
    }
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);
  
  const value: OrgContextValue = {
    activeOrgId,
    setActiveOrg,
    orgs,
    isLoading,
    refreshOrgs,
  };
  
  return (
    <OrgContext.Provider value={value}>
      {children}
    </OrgContext.Provider>
  );
}

