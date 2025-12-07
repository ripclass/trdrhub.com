/**
 * Importer Feature Flags
 * 
 * Re-exports from the unified FeatureFlagService for backward compatibility.
 * New code should import directly from './featureFlagService'.
 */
export type { ImporterFeatureFlag } from './featureFlagService';

export {
  isImporterFeatureEnabled,
  setImporterFeatureFlag,
  getImporterFeatureFlags,
  resetImporterFeatureFlags,
  getImporterFeatureFlagsDefault,
} from './featureFlagService';

