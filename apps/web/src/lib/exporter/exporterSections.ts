// Exporter Dashboard Section Model

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
      return 'reviews';
    case 'customs':
      return 'reviews';
    default:
      return 'reviews';
  }
}

// Sidebar section type — Phase 4/1 slimmed this to the 4-item minimum.
// Reviews content is still reachable via the Recent Activity "View all →"
// link on the dashboard, but it no longer has its own sidebar item.
export type SidebarSection =
  | 'dashboard'
  | 'upload'
  | 'billing'
  | 'settings';

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
    case 'analytics':
    case 'customs':
      // Reviews-content surfaces render as part of the dashboard now;
      // the sidebar highlight stays on Dashboard while any of them are
      // the active content section.
      return 'dashboard';
    default:
      return 'dashboard';
  }
}

/**
 * Map sidebar section to ExporterSection.
 */
export function sidebarToSection(sidebar: SidebarSection): ExporterSection | SidebarSection {
  switch (sidebar) {
    case 'dashboard':
      return 'overview';
    case 'upload':
      return 'upload';
    // billing and settings are handled directly by the dashboard, not via ExporterSection
    case 'billing':
    case 'settings':
      return sidebar;
    default:
      return 'overview';
  }
}
