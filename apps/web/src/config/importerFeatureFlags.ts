// Feature flags for Importer-specific features

export type ImporterFeatureFlag = 
  | "importer_bank_precheck"  // Allow importers to request bank review
  | "supplier_fix_pack";      // Enable supplier fix pack generation

type ImporterFeatureFlagsState = Record<ImporterFeatureFlag, boolean>;

const DEFAULT_FLAGS: ImporterFeatureFlagsState = {
  importer_bank_precheck: true,   // Default ON - verified feature per launch plan
  supplier_fix_pack: false,       // Default OFF - unless verified per launch plan
};

const STORAGE_KEY = "importer:featureFlags";

const isBrowser = typeof window !== "undefined";

function readFromStorage(): ImporterFeatureFlagsState | null {
  if (!isBrowser) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<ImporterFeatureFlagsState>;
    return {
      ...DEFAULT_FLAGS,
      ...parsed,
    } satisfies ImporterFeatureFlagsState;
  } catch (error) {
    console.warn("Failed to read importer feature flags from storage", error);
    return null;
  }
}

function writeToStorage(flags: ImporterFeatureFlagsState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
  } catch (error) {
    console.warn("Failed to persist importer feature flags", error);
  }
}

let cachedFlags: ImporterFeatureFlagsState | null = null;

export function getImporterFeatureFlags(): ImporterFeatureFlagsState {
  if (cachedFlags) return cachedFlags;
  cachedFlags = readFromStorage() ?? { ...DEFAULT_FLAGS };
  return cachedFlags;
}

export function isImporterFeatureEnabled(flag: ImporterFeatureFlag): boolean {
  return getImporterFeatureFlags()[flag];
}

export function setImporterFeatureFlag(flag: ImporterFeatureFlag, enabled: boolean) {
  const next = { ...getImporterFeatureFlags(), [flag]: enabled } as ImporterFeatureFlagsState;
  cachedFlags = next;
  writeToStorage(next);
}

export function resetImporterFeatureFlags() {
  cachedFlags = { ...DEFAULT_FLAGS };
  writeToStorage(cachedFlags);
}

export function getImporterFeatureFlagsDefault(): ImporterFeatureFlagsState {
  return { ...DEFAULT_FLAGS };
}

