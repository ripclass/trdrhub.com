// Feature flags for Exporter-specific features

export type ExporterFeatureFlag = 
  | "exporter_bank_submission"      // Enable bank submission workflow
  | "exporter_customs_pack_pdf"     // Generate PDF coversheet for customs pack
  | "bank_selector_multi";          // Allow selecting multiple banks

type ExporterFeatureFlagsState = Record<ExporterFeatureFlag, boolean>;

const DEFAULT_FLAGS: ExporterFeatureFlagsState = {
  exporter_bank_submission: true,   // Default ON - core feature
  exporter_customs_pack_pdf: true,  // Default ON - PDF coversheet
  bank_selector_multi: false,        // Default OFF - single bank selection
};

const STORAGE_KEY = "exporter:featureFlags";

const isBrowser = typeof window !== "undefined";

function readFromStorage(): ExporterFeatureFlagsState | null {
  if (!isBrowser) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ExporterFeatureFlagsState>;
    return {
      ...DEFAULT_FLAGS,
      ...parsed,
    } satisfies ExporterFeatureFlagsState;
  } catch (error) {
    console.warn("Failed to read exporter feature flags from storage", error);
    return null;
  }
}

function writeToStorage(flags: ExporterFeatureFlagsState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
  } catch (error) {
    console.warn("Failed to persist exporter feature flags", error);
  }
}

let cachedFlags: ExporterFeatureFlagsState | null = null;

export function getExporterFeatureFlags(): ExporterFeatureFlagsState {
  if (cachedFlags) return cachedFlags;
  cachedFlags = readFromStorage() ?? { ...DEFAULT_FLAGS };
  return cachedFlags;
}

export function isExporterFeatureEnabled(flag: ExporterFeatureFlag): boolean {
  return getExporterFeatureFlags()[flag];
}

export function setExporterFeatureFlag(flag: ExporterFeatureFlag, enabled: boolean) {
  const next = { ...getExporterFeatureFlags(), [flag]: enabled } as ExporterFeatureFlagsState;
  cachedFlags = next;
  writeToStorage(next);
}

export function resetExporterFeatureFlags() {
  cachedFlags = { ...DEFAULT_FLAGS };
  writeToStorage(cachedFlags);
}

export function getExporterFeatureFlagsDefault(): ExporterFeatureFlagsState {
  return { ...DEFAULT_FLAGS };
}

