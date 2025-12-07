/**
 * Unified Feature Flag Service
 * 
 * Centralizes all feature flags across the application with:
 * - Type-safe flag definitions
 * - localStorage persistence
 * - Environment variable overrides
 * - Grouped by domain (admin, exporter, importer, lcopilot)
 */

// ============================================================================
// Flag Type Definitions
// ============================================================================

/** Admin console feature flags */
export type AdminFeatureFlag = 
  | "billing"     // Billing management section
  | "partners"    // Partner integrations section
  | "llm"         // LLM configuration section
  | "compliance"; // Compliance settings section

/** Exporter-specific feature flags */
export type ExporterFeatureFlag = 
  | "exporter_bank_submission"  // Enable bank submission workflow
  | "exporter_customs_pack_pdf" // Generate PDF coversheet for customs pack
  | "bank_selector_multi";      // Allow selecting multiple banks

/** Importer-specific feature flags */
export type ImporterFeatureFlag = 
  | "importer_bank_precheck" // Allow importers to request bank review
  | "supplier_fix_pack";     // Enable supplier fix pack generation

/** LCopilot validation feature flags */
export type LCopilotFeatureFlag = 
  | "ai_enrichment"       // Enable AI-powered insights and suggestions
  | "bank_profiles"       // Show bank strictness profiles
  | "schema_validation"   // Runtime API response validation (dev mode)
  | "sanctions_screening" // Enable sanctions screening checks
  | "tolerance_badges"    // Show tolerance explanation badges
  | "amendment_gen"       // Enable MT707/ISO20022 amendment generation
  | "confidence_display"  // Show extraction confidence indicators
  | "two_stage_audit";    // Show detailed two-stage validation audit

/** All feature flag types */
export type FeatureFlag = 
  | AdminFeatureFlag 
  | ExporterFeatureFlag 
  | ImporterFeatureFlag 
  | LCopilotFeatureFlag;

/** Flag domain groups */
export type FlagDomain = "admin" | "exporter" | "importer" | "lcopilot";

// ============================================================================
// Default Values
// ============================================================================

const ADMIN_DEFAULTS: Record<AdminFeatureFlag, boolean> = {
  billing: true,
  partners: true,
  llm: true,
  compliance: true,
};

const EXPORTER_DEFAULTS: Record<ExporterFeatureFlag, boolean> = {
  exporter_bank_submission: true,
  exporter_customs_pack_pdf: true,
  bank_selector_multi: false,
};

const IMPORTER_DEFAULTS: Record<ImporterFeatureFlag, boolean> = {
  importer_bank_precheck: true,
  supplier_fix_pack: false,
};

const LCOPILOT_DEFAULTS: Record<LCopilotFeatureFlag, boolean> = {
  ai_enrichment: true,         // ON - core feature
  bank_profiles: true,         // ON - shows bank strictness
  schema_validation: false,    // OFF in prod - enabled by env var in dev
  sanctions_screening: true,   // ON - compliance requirement
  tolerance_badges: true,      // ON - helps users understand tolerances
  amendment_gen: true,         // ON - MT707/ISO20022 generation
  confidence_display: true,    // ON - shows extraction confidence
  two_stage_audit: false,      // OFF - verbose, for debugging
};

// ============================================================================
// Storage Keys
// ============================================================================

const STORAGE_KEYS: Record<FlagDomain, string> = {
  admin: "admin:featureFlags",
  exporter: "exporter:featureFlags",
  importer: "importer:featureFlags",
  lcopilot: "lcopilot:featureFlags",
};

// ============================================================================
// Environment Variable Overrides
// ============================================================================

/**
 * Check for environment variable overrides.
 * Format: VITE_FF_{FLAG_NAME}=true|false
 * Example: VITE_FF_AI_ENRICHMENT=false
 */
function getEnvOverride(flag: FeatureFlag): boolean | null {
  if (typeof import.meta?.env === "undefined") return null;
  
  const envKey = `VITE_FF_${flag.toUpperCase()}`;
  const value = (import.meta.env as Record<string, string | undefined>)[envKey];
  
  if (value === "true") return true;
  if (value === "false") return false;
  return null;
}

/**
 * Check if we're in development mode
 */
function isDev(): boolean {
  return import.meta?.env?.DEV === true;
}

// ============================================================================
// Internal State Management
// ============================================================================

const isBrowser = typeof window !== "undefined";

type FlagsState = {
  admin: Record<AdminFeatureFlag, boolean>;
  exporter: Record<ExporterFeatureFlag, boolean>;
  importer: Record<ImporterFeatureFlag, boolean>;
  lcopilot: Record<LCopilotFeatureFlag, boolean>;
};

const DEFAULTS: FlagsState = {
  admin: ADMIN_DEFAULTS,
  exporter: EXPORTER_DEFAULTS,
  importer: IMPORTER_DEFAULTS,
  lcopilot: LCOPILOT_DEFAULTS,
};

// In-memory cache
let cache: FlagsState | null = null;

function readFromStorage<T extends FlagDomain>(domain: T): FlagsState[T] | null {
  if (!isBrowser) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS[domain]);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FlagsState[T]>;
    return {
      ...DEFAULTS[domain],
      ...parsed,
    } as FlagsState[T];
  } catch (error) {
    console.warn(`Failed to read ${domain} feature flags from storage`, error);
    return null;
  }
}

function writeToStorage<T extends FlagDomain>(domain: T, flags: FlagsState[T]): void {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEYS[domain], JSON.stringify(flags));
  } catch (error) {
    console.warn(`Failed to persist ${domain} feature flags`, error);
  }
}

function getCache(): FlagsState {
  if (cache) return cache;
  
  cache = {
    admin: readFromStorage("admin") ?? { ...ADMIN_DEFAULTS },
    exporter: readFromStorage("exporter") ?? { ...EXPORTER_DEFAULTS },
    importer: readFromStorage("importer") ?? { ...IMPORTER_DEFAULTS },
    lcopilot: readFromStorage("lcopilot") ?? { ...LCOPILOT_DEFAULTS },
  };
  
  // Apply dev-mode defaults
  if (isDev()) {
    cache.lcopilot.schema_validation = true; // Enable in dev by default
  }
  
  return cache;
}

// ============================================================================
// Public API
// ============================================================================

/**
 * Check if a feature flag is enabled
 * Priority: Environment override > localStorage > default
 */
export function isFeatureEnabled(flag: FeatureFlag): boolean {
  // 1. Check environment override first
  const envOverride = getEnvOverride(flag);
  if (envOverride !== null) return envOverride;
  
  // 2. Check cached/stored value
  const state = getCache();
  
  if (flag in state.admin) return state.admin[flag as AdminFeatureFlag];
  if (flag in state.exporter) return state.exporter[flag as ExporterFeatureFlag];
  if (flag in state.importer) return state.importer[flag as ImporterFeatureFlag];
  if (flag in state.lcopilot) return state.lcopilot[flag as LCopilotFeatureFlag];
  
  console.warn(`Unknown feature flag: ${flag}`);
  return false;
}

/**
 * Set a feature flag value
 */
export function setFeatureFlag(flag: FeatureFlag, enabled: boolean): void {
  const state = getCache();
  
  if (flag in ADMIN_DEFAULTS) {
    state.admin[flag as AdminFeatureFlag] = enabled;
    writeToStorage("admin", state.admin);
  } else if (flag in EXPORTER_DEFAULTS) {
    state.exporter[flag as ExporterFeatureFlag] = enabled;
    writeToStorage("exporter", state.exporter);
  } else if (flag in IMPORTER_DEFAULTS) {
    state.importer[flag as ImporterFeatureFlag] = enabled;
    writeToStorage("importer", state.importer);
  } else if (flag in LCOPILOT_DEFAULTS) {
    state.lcopilot[flag as LCopilotFeatureFlag] = enabled;
    writeToStorage("lcopilot", state.lcopilot);
  } else {
    console.warn(`Cannot set unknown feature flag: ${flag}`);
  }
}

/**
 * Get all flags for a domain
 */
export function getFeatureFlags<T extends FlagDomain>(domain: T): FlagsState[T] {
  return { ...getCache()[domain] };
}

/**
 * Get default values for a domain
 */
export function getFeatureFlagsDefaults<T extends FlagDomain>(domain: T): FlagsState[T] {
  return { ...DEFAULTS[domain] };
}

/**
 * Reset all flags in a domain to defaults
 */
export function resetFeatureFlags(domain: FlagDomain): void {
  const state = getCache();
  state[domain] = { ...DEFAULTS[domain] } as FlagsState[typeof domain];
  writeToStorage(domain, state[domain]);
}

/**
 * Reset all flags across all domains
 */
export function resetAllFeatureFlags(): void {
  cache = {
    admin: { ...ADMIN_DEFAULTS },
    exporter: { ...EXPORTER_DEFAULTS },
    importer: { ...IMPORTER_DEFAULTS },
    lcopilot: { ...LCOPILOT_DEFAULTS },
  };
  
  writeToStorage("admin", cache.admin);
  writeToStorage("exporter", cache.exporter);
  writeToStorage("importer", cache.importer);
  writeToStorage("lcopilot", cache.lcopilot);
}

/**
 * Get all feature flags as a flat object (useful for debugging)
 */
export function getAllFeatureFlags(): Record<FeatureFlag, boolean> {
  const state = getCache();
  return {
    ...state.admin,
    ...state.exporter,
    ...state.importer,
    ...state.lcopilot,
  };
}

/**
 * List all available flag names by domain
 */
export function listAvailableFlags(): Record<FlagDomain, FeatureFlag[]> {
  return {
    admin: Object.keys(ADMIN_DEFAULTS) as AdminFeatureFlag[],
    exporter: Object.keys(EXPORTER_DEFAULTS) as ExporterFeatureFlag[],
    importer: Object.keys(IMPORTER_DEFAULTS) as ImporterFeatureFlag[],
    lcopilot: Object.keys(LCOPILOT_DEFAULTS) as LCopilotFeatureFlag[],
  };
}

// ============================================================================
// Convenience Shortcuts (domain-specific) - Backward Compatible
// ============================================================================

// Admin
export const isAdminFeatureEnabled = (flag: AdminFeatureFlag) => isFeatureEnabled(flag);
export const setAdminFeatureFlag = (flag: AdminFeatureFlag, enabled: boolean) => setFeatureFlag(flag, enabled);
export const getAdminFeatureFlags = () => getFeatureFlags("admin");
export const resetAdminFeatureFlags = () => resetFeatureFlags("admin");
export const getAdminFeatureFlagsDefault = () => getFeatureFlagsDefaults("admin");

// Exporter
export const isExporterFeatureEnabled = (flag: ExporterFeatureFlag) => isFeatureEnabled(flag);
export const setExporterFeatureFlag = (flag: ExporterFeatureFlag, enabled: boolean) => setFeatureFlag(flag, enabled);
export const getExporterFeatureFlags = () => getFeatureFlags("exporter");
export const resetExporterFeatureFlags = () => resetFeatureFlags("exporter");
export const getExporterFeatureFlagsDefault = () => getFeatureFlagsDefaults("exporter");

// Importer
export const isImporterFeatureEnabled = (flag: ImporterFeatureFlag) => isFeatureEnabled(flag);
export const setImporterFeatureFlag = (flag: ImporterFeatureFlag, enabled: boolean) => setFeatureFlag(flag, enabled);
export const getImporterFeatureFlags = () => getFeatureFlags("importer");
export const resetImporterFeatureFlags = () => resetFeatureFlags("importer");
export const getImporterFeatureFlagsDefault = () => getFeatureFlagsDefaults("importer");

// LCopilot
export const isLCopilotFeatureEnabled = (flag: LCopilotFeatureFlag) => isFeatureEnabled(flag);
export const setLCopilotFeatureFlag = (flag: LCopilotFeatureFlag, enabled: boolean) => setFeatureFlag(flag, enabled);
export const getLCopilotFeatureFlags = () => getFeatureFlags("lcopilot");
export const resetLCopilotFeatureFlags = () => resetFeatureFlags("lcopilot");
export const getLCopilotFeatureFlagsDefault = () => getFeatureFlagsDefaults("lcopilot");
