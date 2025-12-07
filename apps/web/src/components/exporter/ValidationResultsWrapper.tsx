/**
 * Validation Results Wrapper
 * 
 * Switches between V1 and V2 validation results based on feature flags.
 */

import { useFeature } from '@/config/features-v2';
import { ValidationResultsV2 } from '@/components/v2/ValidationResultsV2';
import type { ValidationResultsV2Data } from '@/components/v2/ValidationResultsV2';

interface ValidationResultsWrapperProps {
  // V2 Data (when using V2 API)
  v2Data?: ValidationResultsV2Data;
  
  // V1 Data (when using V1 API)
  v1Data?: any;
  
  // Handlers
  onRevalidate?: () => void;
  onDownload?: () => void;
  onAmendment?: (issue: any) => void;
  onSubmit?: () => void;
  
  // Force V2 (for testing)
  forceV2?: boolean;
  
  // Children (V1 fallback)
  children?: React.ReactNode;
}

export function ValidationResultsWrapper({
  v2Data,
  v1Data,
  onRevalidate,
  onDownload,
  onAmendment,
  onSubmit,
  forceV2 = false,
  children,
}: ValidationResultsWrapperProps) {
  const useV2Results = useFeature('USE_V2_RESULTS');
  
  // Use V2 if:
  // 1. Feature flag enabled for user AND we have V2 data
  // 2. OR forceV2 is true AND we have V2 data
  const shouldUseV2 = (useV2Results || forceV2) && v2Data;
  
  if (shouldUseV2 && v2Data) {
    return (
      <ValidationResultsV2
        data={v2Data}
        onRevalidate={onRevalidate}
        onDownload={onDownload}
        onAmendment={onAmendment}
        onSubmit={onSubmit}
      />
    );
  }
  
  // Fall back to V1 (children)
  return <>{children}</>;
}

export default ValidationResultsWrapper;

