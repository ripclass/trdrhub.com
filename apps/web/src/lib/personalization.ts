/**
 * Personalization Service
 * Manages user preferences: pinned tabs, default landing page per role
 */
import { useAuth } from "@/hooks/use-auth";

export interface UserPreferences {
  pinnedTabs: string[];
  defaultLanding: string;
  dashboard: 'bank' | 'exporter' | 'importer' | 'admin';
  role?: string;
}

const STORAGE_KEY = 'lcopilot_user_preferences';

/**
 * Get user preferences
 */
export function getUserPreferences(
  dashboard: UserPreferences['dashboard'],
  role?: string
): UserPreferences {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) {
      // Return defaults based on role
      return getDefaultPreferences(dashboard, role);
    }
    
    const prefs: UserPreferences[] = JSON.parse(stored);
    const userPrefs = prefs.find(
      (p) => p.dashboard === dashboard && (!role || p.role === role)
    );
    
    return userPrefs || getDefaultPreferences(dashboard, role);
  } catch (error) {
    console.error('Failed to load user preferences:', error);
    return getDefaultPreferences(dashboard, role);
  }
}

/**
 * Get default preferences based on role
 */
function getDefaultPreferences(
  dashboard: UserPreferences['dashboard'],
  role?: string
): UserPreferences {
  const defaults: Record<string, Record<string, string>> = {
    bank: {
      admin: 'dashboard',
      approver: 'approvals',
      reviewer: 'queue',
      analyst: 'results',
      default: 'dashboard',
    },
    exporter: {
      owner: 'dashboard',
      editor: 'workspace',
      viewer: 'reviews',
      default: 'dashboard',
    },
    importer: {
      owner: 'dashboard',
      editor: 'workspace',
      viewer: 'reviews',
      default: 'dashboard',
    },
    admin: {
      default: 'overview',
    },
  };

  const dashboardDefaults = defaults[dashboard] || {};
  const defaultLanding = role ? dashboardDefaults[role] || dashboardDefaults.default : dashboardDefaults.default;

  return {
    pinnedTabs: [],
    defaultLanding: defaultLanding || 'dashboard',
    dashboard,
    role,
  };
}

/**
 * Save user preferences
 */
export function saveUserPreferences(prefs: UserPreferences): void {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    const allPrefs: UserPreferences[] = stored ? JSON.parse(stored) : [];
    
    // Remove existing preferences for this dashboard/role
    const filtered = allPrefs.filter(
      (p) => !(p.dashboard === prefs.dashboard && p.role === prefs.role)
    );
    
    // Add new preferences
    const updated = [...filtered, prefs];
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch (error) {
    console.error('Failed to save user preferences:', error);
  }
}

/**
 * Pin a tab
 */
export function pinTab(
  dashboard: UserPreferences['dashboard'],
  tab: string,
  role?: string
): void {
  const prefs = getUserPreferences(dashboard, role);
  if (!prefs.pinnedTabs.includes(tab)) {
    prefs.pinnedTabs = [...prefs.pinnedTabs, tab];
    saveUserPreferences(prefs);
  }
}

/**
 * Unpin a tab
 */
export function unpinTab(
  dashboard: UserPreferences['dashboard'],
  tab: string,
  role?: string
): void {
  const prefs = getUserPreferences(dashboard, role);
  prefs.pinnedTabs = prefs.pinnedTabs.filter((t) => t !== tab);
  saveUserPreferences(prefs);
}

/**
 * Set default landing page
 */
export function setDefaultLanding(
  dashboard: UserPreferences['dashboard'],
  landing: string,
  role?: string
): void {
  const prefs = getUserPreferences(dashboard, role);
  prefs.defaultLanding = landing;
  saveUserPreferences(prefs);
}

/**
 * Get default landing page for current user
 */
export function getDefaultLanding(
  dashboard: UserPreferences['dashboard'],
  role?: string
): string {
  const prefs = getUserPreferences(dashboard, role);
  return prefs.defaultLanding;
}

