export type AdminFeatureFlag = "billing" | "partners" | "llm" | "compliance";

type FeatureFlagsState = Record<AdminFeatureFlag, boolean>;

const DEFAULT_FLAGS: FeatureFlagsState = {
  billing: true,
  partners: true,
  llm: true,
  compliance: true,
};

const STORAGE_KEY = "admin:featureFlags";

const isBrowser = typeof window !== "undefined";

function readFromStorage(): FeatureFlagsState | null {
  if (!isBrowser) return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<FeatureFlagsState>;
    return {
      ...DEFAULT_FLAGS,
      ...parsed,
    } satisfies FeatureFlagsState;
  } catch (error) {
    console.warn("Failed to read admin feature flags from storage", error);
    return null;
  }
}

function writeToStorage(flags: FeatureFlagsState) {
  if (!isBrowser) return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
  } catch (error) {
    console.warn("Failed to persist admin feature flags", error);
  }
}

let cachedFlags: FeatureFlagsState | null = null;

export function getAdminFeatureFlags(): FeatureFlagsState {
  if (cachedFlags) return cachedFlags;
  cachedFlags = readFromStorage() ?? { ...DEFAULT_FLAGS };
  return cachedFlags;
}

export function isAdminFeatureEnabled(flag: AdminFeatureFlag): boolean {
  return getAdminFeatureFlags()[flag];
}

export function setAdminFeatureFlag(flag: AdminFeatureFlag, enabled: boolean) {
  const next = { ...getAdminFeatureFlags(), [flag]: enabled } as FeatureFlagsState;
  cachedFlags = next;
  writeToStorage(next);
}

export function resetAdminFeatureFlags() {
  cachedFlags = { ...DEFAULT_FLAGS };
  writeToStorage(cachedFlags);
}

export function getAdminFeatureFlagsDefault(): FeatureFlagsState {
  return { ...DEFAULT_FLAGS };
}

