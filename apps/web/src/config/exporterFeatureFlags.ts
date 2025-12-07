/**
 * Exporter Feature Flags
 * 
 * Re-exports from the unified FeatureFlagService for backward compatibility.
 * New code should import directly from './featureFlagService'.
 */
export type { ExporterFeatureFlag } from './featureFlagService';

export {
  isExporterFeatureEnabled,
  setExporterFeatureFlag,
  getExporterFeatureFlags,
  resetExporterFeatureFlags,
  getExporterFeatureFlagsDefault,
} from './featureFlagService';

