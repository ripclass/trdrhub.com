/**
 * LCopilot V2 Feature Flags
 * 
 * Controls gradual rollout of V2 components.
 * 
 * Usage:
 *   const useV2 = useFeature('USE_V2_RESULTS');
 *   if (useV2) {
 *     return <ValidationResultsV2 {...props} />;
 *   }
 *   return <ExporterResults {...props} />;
 */

// Feature flag configuration
export interface FeatureConfig {
  enabled: boolean;
  rolloutPercent: number;  // 0-100
  allowlist: string[];     // Email addresses with access
  description: string;
}

export const FEATURES: Record<string, FeatureConfig> = {
  // V2 Validation Results
  USE_V2_RESULTS: {
    enabled: true,
    rolloutPercent: 0,  // Start at 0%, gradually increase
    allowlist: ['imran@iec.com', 'admin@trdr.io'],  // Test users for V2
    description: 'Use V2 validation results component with citations',
  },
  
  // V2 Unified Dashboard
  USE_V2_DASHBOARD: {
    enabled: true,
    rolloutPercent: 0,
    allowlist: [],
    description: 'Use unified V2 dashboard instead of role-specific dashboards',
  },
  
  // V2 Issue Cards with Citations
  USE_V2_ISSUES: {
    enabled: true,
    rolloutPercent: 0,
    allowlist: [],
    description: 'Use V2 issue cards with UCP600/ISBP745 citations',
  },
  
  // V2 Extraction Pipeline (Ensemble AI)
  USE_V2_EXTRACTION: {
    enabled: true,
    rolloutPercent: 100,  // Already deployed via ensemble extractor
    allowlist: [],
    description: 'Use V2 ensemble AI extraction',
  },
  
  // V2 Preprocessing (Image enhancement)
  USE_V2_PREPROCESSING: {
    enabled: false,
    rolloutPercent: 0,
    allowlist: [],
    description: 'Use V2 image preprocessing with enhancement',
  },
  
  // V2 API Endpoint
  USE_V2_API: {
    enabled: true,
    rolloutPercent: 0,
    allowlist: ['imran@iec.com', 'admin@trdr.io'],  // Test users for V2
    description: 'Use /api/v2/validate endpoint',
  },
  
  // Smart AI Routing
  USE_SMART_AI_ROUTING: {
    enabled: true,
    rolloutPercent: 0,
    allowlist: [],
    description: 'Route to best AI provider based on document type',
  },
  
  // Real Data (No Mocks)
  USE_REAL_DATA: {
    enabled: true,
    rolloutPercent: 100,  // Force real data for everyone
    allowlist: [],
    description: 'Use real API data instead of mock data',
  },
};

// User hash for consistent rollout
function hashUser(userId: string): number {
  let hash = 0;
  for (let i = 0; i < userId.length; i++) {
    const char = userId.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash; // Convert to 32bit integer
  }
  return Math.abs(hash % 100);
}

// Check if user is in rollout
export function isInRollout(userId: string, rolloutPercent: number): boolean {
  if (rolloutPercent >= 100) return true;
  if (rolloutPercent <= 0) return false;
  return hashUser(userId) < rolloutPercent;
}

// Check if user has feature access
export function hasFeatureAccess(
  featureName: keyof typeof FEATURES,
  userId?: string,
  userEmail?: string,
): boolean {
  const feature = FEATURES[featureName];
  if (!feature) return false;
  if (!feature.enabled) return false;
  
  // Check allowlist first
  if (userEmail && feature.allowlist.includes(userEmail)) {
    return true;
  }
  
  // Check rollout percentage
  if (userId && isInRollout(userId, feature.rolloutPercent)) {
    return true;
  }
  
  // Default: only if 100% rollout
  return feature.rolloutPercent >= 100;
}

// React hook for feature flags
import { useMemo } from 'react';
import { useAuth } from '@/hooks/use-auth';

export function useFeature(featureName: keyof typeof FEATURES): boolean {
  const { user } = useAuth();
  
  return useMemo(() => {
    return hasFeatureAccess(featureName, user?.id, user?.email);
  }, [featureName, user?.id, user?.email]);
}

// React component for conditional rendering
interface FeatureProps {
  name: keyof typeof FEATURES;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function Feature({ name, children, fallback = null }: FeatureProps): JSX.Element | null {
  const hasAccess = useFeature(name);
  
  if (hasAccess) {
    return <>{children}</>;
  }
  
  return <>{fallback}</>;
}

// Get all enabled features for current user
export function useEnabledFeatures(): string[] {
  const { user } = useAuth();
  
  return useMemo(() => {
    return Object.keys(FEATURES).filter(name => 
      hasFeatureAccess(name as keyof typeof FEATURES, user?.id, user?.email)
    );
  }, [user?.id, user?.email]);
}

// Admin: Update feature config (for future admin panel)
export function updateFeature(
  featureName: keyof typeof FEATURES,
  updates: Partial<FeatureConfig>
): void {
  const feature = FEATURES[featureName];
  if (feature) {
    Object.assign(feature, updates);
  }
}

// Debug: Log feature status
export function logFeatureStatus(userId?: string, userEmail?: string): void {
  console.group('🚩 Feature Flags Status');
  
  for (const [name, config] of Object.entries(FEATURES)) {
    const hasAccess = hasFeatureAccess(
      name as keyof typeof FEATURES,
      userId,
      userEmail
    );
    
    console.log(
      `${hasAccess ? '✅' : '❌'} ${name}: ${config.description}`,
      `(${config.rolloutPercent}% rollout, ${config.allowlist.length} allowlist)`
    );
  }
  
  console.groupEnd();
}

