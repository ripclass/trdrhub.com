/**
 * useDashboardBase Hook
 * 
 * Shared state management for Exporter and Importer dashboards.
 * Handles authentication, session loading, and section navigation.
 */

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { getUserSessions, type ValidationSession } from "@/api/sessions";
import { calculateDashboardStats, sessionsToHistory, formatTimeAgo, type DashboardStats, type HistoryItem } from "./utils";

export interface DashboardBaseOptions {
  /** Role for stats calculation (exporter uses all discrepancies, importer uses critical-only) */
  role: "exporter" | "importer";
  /** Login redirect path */
  loginPath: string;
  /** Default section when none specified */
  defaultSection?: string;
}

export interface DashboardBaseReturn {
  // Navigation
  activeSection: string;
  searchParams: URLSearchParams;
  setActiveSection: (section: string) => void;
  handleSectionChange: (section: string, extras?: Record<string, string | undefined>) => void;
  
  // Sessions
  sessions: ValidationSession[];
  isLoadingSessions: boolean;
  
  // Computed stats
  stats: DashboardStats;
  recentHistory: HistoryItem[];
  
  // Utilities
  formatTimeAgo: typeof formatTimeAgo;
  
  // Billing
  billingTab: string;
  setBillingTab: (tab: string) => void;
  handleBillingTabChange: (tab: string) => void;
}

export function useDashboardBase(
  isAuthenticated: boolean,
  authLoading: boolean,
  options: DashboardBaseOptions
): DashboardBaseReturn {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  
  const { role, loginPath, defaultSection = "dashboard" } = options;
  
  // Section state
  const [activeSection, setActiveSection] = useState<string>(() => {
    const sectionParam = searchParams.get("section");
    return sectionParam || defaultSection;
  });
  
  // Sessions state
  const [sessions, setSessions] = useState<ValidationSession[]>([]);
  const [isLoadingSessions, setIsLoadingSessions] = useState(true);
  
  // Billing tab state
  const [billingTab, setBillingTab] = useState<string>("overview");

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      const returnUrl = encodeURIComponent(window.location.pathname + window.location.search);
      if (loginPath.includes("?")) {
        navigate(`${loginPath}&returnUrl=${returnUrl}`);
      } else {
        navigate(`${loginPath}?returnUrl=${returnUrl}`);
      }
    }
  }, [isAuthenticated, authLoading, navigate, loginPath]);

  // Load validation sessions
  useEffect(() => {
    const loadSessions = async () => {
      if (!isAuthenticated) return;
      
      setIsLoadingSessions(true);
      try {
        const data = await getUserSessions();
        setSessions(data || []);
      } catch (error) {
        console.error("Failed to load validation sessions:", error);
        setSessions([]);
      } finally {
        setIsLoadingSessions(false);
      }
    };
    loadSessions();
  }, [isAuthenticated]);

  // Sync section from URL
  useEffect(() => {
    const sectionParam = searchParams.get("section");
    const legacyTab = searchParams.get("tab");
    
    if (sectionParam && sectionParam !== activeSection) {
      setActiveSection(sectionParam);
    } else if (!sectionParam && legacyTab) {
      // Handle legacy tab param
      const legacyMap: Record<string, string> = {
        results: "reviews",
        notifications: "notifications",
        analytics: "analytics",
        upload: "upload",
      };
      const mapped = legacyMap[legacyTab] || defaultSection;
      setActiveSection(mapped);
    } else if (!sectionParam) {
      setActiveSection(defaultSection);
    }
  }, [searchParams, activeSection, defaultSection]);

  // Section change handler
  const handleSectionChange = useCallback(
    (section: string, extras: Record<string, string | undefined> = {}) => {
      setActiveSection(section);
      
      const params = new URLSearchParams(searchParams);
      
      // Clean up old params for non-matching sections
      if (section === "dashboard" || section === "overview") {
        params.delete("section");
      } else {
        params.set("section", section);
      }
      
      // Remove params that don't apply to this section
      if (section !== "upload") {
        params.delete("draft_id");
        params.delete("type");
      }
      if (section !== "reviews") {
        params.delete("jobId");
        params.delete("lc");
        params.delete("mode");
      }
      params.delete("tab"); // Legacy param
      
      // Apply extras
      Object.entries(extras).forEach(([key, value]) => {
        if (!value) {
          params.delete(key);
        } else {
          params.set(key, value);
        }
      });
      
      setSearchParams(params, { replace: true });
    },
    [searchParams, setSearchParams]
  );

  // Billing tab handler
  const handleBillingTabChange = useCallback(
    (tab: string) => {
      setBillingTab(tab);
      const sectionMap: Record<string, string> = {
        overview: "billing",
        usage: "billing-usage",
        invoices: "billing",
      };
      const section = sectionMap[tab] || "billing";
      handleSectionChange(section);
    },
    [handleSectionChange]
  );

  // Calculate stats based on role
  const stats = calculateDashboardStats(sessions, {
    criticalOnly: role === "importer",
  });

  // Get recent history
  const recentHistory = sessionsToHistory(sessions, {
    limit: 5,
    partyField: role === "importer" ? "beneficiary" : "applicant",
    criticalOnly: role === "importer",
  });

  return {
    // Navigation
    activeSection,
    searchParams,
    setActiveSection,
    handleSectionChange,
    
    // Sessions
    sessions,
    isLoadingSessions,
    
    // Computed stats
    stats,
    recentHistory,
    
    // Utilities
    formatTimeAgo,
    
    // Billing
    billingTab,
    setBillingTab,
    handleBillingTabChange,
  };
}

