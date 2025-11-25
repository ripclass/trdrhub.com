// Exporter Dashboard Section Model
// Mirrors importer architecture for consistency

export type ExporterSection =
  | 'overview'
  | 'upload'
  | 'reviews'
  | 'documents'
  | 'issues'
  | 'extracted-data'
  | 'history'
  | 'analytics'
  | 'customs';

export const EXPORTER_SECTION_OPTIONS: ExporterSection[] = [
  'overview',
  'upload',
  'reviews',
  'documents',
  'issues',
  'extracted-data',
  'history',
  'analytics',
  'customs',
];

/**
 * Parse a URL section parameter into a valid ExporterSection.
 * Falls back to 'overview' if invalid or missing.
 */
export function parseExporterSection(raw?: string | null): ExporterSection {
  if (!raw) return 'overview';
  const v = raw.toLowerCase().trim();
  
  // Handle legacy aliases
  if (v === 'discrepancies') return 'issues';
  if (v === 'dashboard') return 'overview';
  
  if (EXPORTER_SECTION_OPTIONS.includes(v as ExporterSection)) {
    return v as ExporterSection;
  }
  
  return 'overview';
}

/**
 * Convert section to URL-safe string.
 */
export function toExporterSectionParam(section: ExporterSection): string {
  return section;
}

/**
 * Map ExporterSection to the ResultsTab value expected by ExporterResults.
 * For non-review sections that show ExporterResults, this determines the initial tab.
 */
export function sectionToResultsTab(section: ExporterSection): string {
  switch (section) {
    case 'overview':
    case 'reviews':
      return 'overview';
    case 'documents':
      return 'documents';
    case 'issues':
      return 'discrepancies'; // ExporterResults uses 'discrepancies' internally
    case 'extracted-data':
      return 'extracted-data';
    case 'history':
      return 'history';
    case 'analytics':
      return 'analytics';
    case 'customs':
      return 'customs';
    default:
      return 'overview';
  }
}

/**
 * Map a ResultsTab (from ExporterResults tab change) back to an ExporterSection.
 */
export function resultsTabToSection(tab: string): ExporterSection {
  switch (tab) {
    case 'overview':
      return 'reviews';
    case 'documents':
      return 'documents';
    case 'discrepancies':
      return 'issues';
    case 'extracted-data':
      return 'extracted-data';
    case 'history':
      return 'history';
    case 'analytics':
      return 'analytics';
    case 'customs':
      return 'customs';
    default:
      return 'reviews';
  }
}

// Sidebar section type (matches ExporterSidebar props)
export type SidebarSection =
  | 'dashboard'
  | 'workspace'
  | 'templates'
  | 'upload'
  | 'reviews'
  | 'analytics'
  | 'notifications'
  | 'billing'
  | 'billing-usage'
  | 'ai-assistance'
  | 'content-library'
  | 'shipment-timeline'
  | 'settings'
  | 'help';

/**
 * Map ExporterSection to the sidebar's section identifier.
 */
export function sectionToSidebar(section: ExporterSection): SidebarSection {
  switch (section) {
    case 'overview':
      return 'dashboard';
    case 'upload':
      return 'upload';
    case 'reviews':
    case 'documents':
    case 'issues':
    case 'extracted-data':
    case 'history':
      return 'reviews';
    case 'analytics':
    case 'customs':
      return 'analytics';
    default:
      return 'dashboard';
  }
}

/**
 * Map sidebar section to ExporterSection (for sidebar click handling).
 */
export function sidebarToSection(sidebar: SidebarSection): ExporterSection | null {
  switch (sidebar) {
    case 'dashboard':
      return 'overview';
    case 'upload':
      return 'upload';
    case 'reviews':
      return 'reviews';
    case 'workspace':
      return 'documents';
    case 'analytics':
      return 'analytics';
    case 'notifications':
      return 'issues';
    default:
      return null; // Other sidebar items don't map to ExporterSection
  }
}

