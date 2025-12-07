/**
 * Admin Feature Flags
 * 
 * Re-exports from the unified FeatureFlagService for backward compatibility.
 * New code should import directly from './featureFlagService'.
 */
export type { AdminFeatureFlag } from './featureFlagService';

export {
  isAdminFeatureEnabled,
  setAdminFeatureFlag,
  getAdminFeatureFlags,
  resetAdminFeatureFlags,
  getAdminFeatureFlagsDefault,
} from './featureFlagService';

