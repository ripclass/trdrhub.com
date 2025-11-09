/**
 * Saved Views & Shared Views Service
 * Provides a unified system for saving, loading, and sharing filter presets across dashboards
 */

export interface SavedView {
  id: string;
  name: string;
  description?: string;
  dashboard: 'bank' | 'exporter' | 'importer' | 'admin';
  section: string; // e.g., 'results', 'queue', 'analytics'
  filters: Record<string, any>;
  isShared: boolean;
  sharedWith?: string[]; // User IDs or team IDs
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  usageCount: number;
}

const STORAGE_KEY = 'lcopilot_saved_views';
const SHARED_VIEWS_KEY = 'lcopilot_shared_views';

/**
 * Get all saved views for a specific dashboard/section
 */
export function getSavedViews(
  dashboard: SavedView['dashboard'],
  section?: string
): SavedView[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (!stored) return [];
    
    const views: SavedView[] = JSON.parse(stored);
    return views.filter(
      (v) => v.dashboard === dashboard && (!section || v.section === section)
    );
  } catch (error) {
    console.error('Failed to load saved views:', error);
    return [];
  }
}

/**
 * Save a new view
 */
export function saveView(view: Omit<SavedView, 'id' | 'createdAt' | 'updatedAt' | 'usageCount'>): SavedView {
  const newView: SavedView = {
    ...view,
    id: `view-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    usageCount: 0,
  };

  const existing = getSavedViews(view.dashboard);
  const updated = [...existing, newView];
  localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  
  return newView;
}

/**
 * Update an existing view
 */
export function updateView(viewId: string, updates: Partial<SavedView>): SavedView | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;

  const views: SavedView[] = JSON.parse(stored);
  const index = views.findIndex((v) => v.id === viewId);
  if (index === -1) return null;

  views[index] = {
    ...views[index],
    ...updates,
    updatedAt: new Date().toISOString(),
  };

  localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
  return views[index];
}

/**
 * Delete a view
 */
export function deleteView(viewId: string): boolean {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return false;

  const views: SavedView[] = JSON.parse(stored);
  const filtered = views.filter((v) => v.id !== viewId);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(filtered));
  
  return filtered.length < views.length;
}

/**
 * Load a view (increments usage count)
 */
export function loadView(viewId: string): SavedView | null {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (!stored) return null;

  const views: SavedView[] = JSON.parse(stored);
  const view = views.find((v) => v.id === viewId);
  if (!view) return null;

  // Increment usage count
  view.usageCount = (view.usageCount || 0) + 1;
  view.updatedAt = new Date().toISOString();
  localStorage.setItem(STORAGE_KEY, JSON.stringify(views));

  return view;
}

/**
 * Share a view with other users/teams
 */
export function shareView(viewId: string, sharedWith: string[]): SavedView | null {
  return updateView(viewId, {
    isShared: true,
    sharedWith,
  });
}

/**
 * Get shared views (for future API integration)
 */
export function getSharedViews(dashboard?: SavedView['dashboard']): SavedView[] {
  try {
    const stored = localStorage.getItem(SHARED_VIEWS_KEY);
    if (!stored) return [];
    
    const views: SavedView[] = JSON.parse(stored);
    return dashboard ? views.filter((v) => v.dashboard === dashboard) : views;
  } catch (error) {
    console.error('Failed to load shared views:', error);
    return [];
  }
}

/**
 * Generate deep link for a view
 */
export function generateDeepLink(view: SavedView, baseUrl: string = window.location.origin): string {
  const params = new URLSearchParams();
  
  // Add dashboard and section
  params.set('dashboard', view.dashboard);
  params.set('section', view.section);
  
  // Add filters as JSON
  params.set('filters', JSON.stringify(view.filters));
  
  // Add view ID for direct loading
  params.set('view', view.id);
  
  return `${baseUrl}/lcopilot/${view.dashboard}-dashboard?${params.toString()}`;
}

/**
 * Parse deep link filters from URL
 */
export function parseDeepLinkFilters(searchParams: URLSearchParams): {
  viewId?: string;
  filters?: Record<string, any>;
  dashboard?: string;
  section?: string;
} {
  const viewId = searchParams.get('view') || undefined;
  const filtersStr = searchParams.get('filters');
  const filters = filtersStr ? JSON.parse(filtersStr) : undefined;
  const dashboard = searchParams.get('dashboard') || undefined;
  const section = searchParams.get('section') || undefined;

  return { viewId, filters, dashboard, section };
}

