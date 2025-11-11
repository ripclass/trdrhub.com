/**
 * FilterBar Component
 * Common filter bar with URL state sync for bank dashboards
 */
import * as React from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { ChevronDown, ChevronUp, Download, FileText, X } from "lucide-react";
import { SavedViewsManager } from "./SavedViewsManager";
import { AdvancedFilters } from "@/components/bank/AdvancedFilters";
import type { BankResultsFilters } from "@/api/bank";

export interface FilterBarProps {
  resource: 'results' | 'jobs';
  onFiltersChange?: (filters: BankResultsFilters) => void;
  onExportCSV?: () => void;
  onExportPDF?: () => void;
  exportLoading?: boolean;
  showAdvancedFilters?: boolean;
}

export function FilterBar({
  resource,
  onFiltersChange,
  onExportCSV,
  onExportPDF,
  exportLoading = false,
  showAdvancedFilters = true,
}: FilterBarProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [isAdvancedOpen, setIsAdvancedOpen] = React.useState(false);

  // Extract filter values from URL
  const q = searchParams.get('q') || '';
  const assignee = searchParams.get('assignee') || '';
  const queue = searchParams.get('queue') || '';
  const status = searchParams.get('status') || 'all';
  const clientName = searchParams.get('client_name') || '';
  const dateRange = searchParams.get('date_range') || '90';
  const sortBy = searchParams.get('sort_by') || 'completed_at';
  const sortOrder = searchParams.get('sort_order') || 'desc';
  const org = searchParams.get('org') || null; // Org filter

  // Advanced filters (stored as JSON in URL)
  const advancedFiltersStr = searchParams.get('advanced_filters');
  const advancedFilters: BankResultsFilters = React.useMemo(() => {
    try {
      return advancedFiltersStr ? JSON.parse(advancedFiltersStr) : {};
    } catch {
      return {};
    }
  }, [advancedFiltersStr]);

  // Update URL params when filters change
  const updateFilters = React.useCallback((updates: Partial<BankResultsFilters>) => {
    const newParams = new URLSearchParams(searchParams);
    
    // Update simple params
    if (updates.q !== undefined) {
      if (updates.q) newParams.set('q', updates.q);
      else newParams.delete('q');
    }
    if (updates.assignee !== undefined) {
      if (updates.assignee) newParams.set('assignee', updates.assignee);
      else newParams.delete('assignee');
    }
    if (updates.queue !== undefined) {
      if (updates.queue) newParams.set('queue', updates.queue);
      else newParams.delete('queue');
    }
    if (updates.status !== undefined) {
      if (updates.status && updates.status !== 'all') newParams.set('status', updates.status);
      else newParams.delete('status');
    }
    if (updates.client_name !== undefined) {
      if (updates.client_name) newParams.set('client_name', updates.client_name);
      else newParams.delete('client_name');
    }
    if (updates.sort_by !== undefined) {
      newParams.set('sort_by', updates.sort_by);
    }
    if (updates.sort_order !== undefined) {
      newParams.set('sort_order', updates.sort_order);
    }

    // Update advanced filters
    if (updates.advancedFilters) {
      newParams.set('advanced_filters', JSON.stringify(updates.advancedFilters));
    }

    setSearchParams(newParams, { replace: true });
    onFiltersChange?.(updates as BankResultsFilters);
  }, [searchParams, setSearchParams, onFiltersChange]);

  // Build current filters object for SavedViewsManager
  const currentFilters = React.useMemo(() => ({
    q,
    assignee,
    queue,
    status,
    client_name: clientName,
    date_range: dateRange,
    sort_by: sortBy,
    sort_order: sortOrder,
    org, // Include org in filters
    advancedFilters,
  }), [q, assignee, queue, status, clientName, dateRange, sortBy, sortOrder, org, advancedFilters]);

  // Handle loading a saved view
  const handleLoadView = React.useCallback((filters: Record<string, any>) => {
    const updates: Partial<BankResultsFilters> = {};
    
    if (filters.q !== undefined) updates.q = filters.q;
    if (filters.assignee !== undefined) updates.assignee = filters.assignee;
    if (filters.queue !== undefined) updates.queue = filters.queue;
    if (filters.status !== undefined) updates.status = filters.status;
    if (filters.client_name !== undefined) updates.client_name = filters.client_name;
    if (filters.date_range !== undefined) {
      // Update date_range param
      const newParams = new URLSearchParams(searchParams);
      newParams.set('date_range', filters.date_range);
      setSearchParams(newParams, { replace: true });
    }
    if (filters.sort_by !== undefined) updates.sort_by = filters.sort_by;
    if (filters.sort_order !== undefined) updates.sort_order = filters.sort_order;
    if (filters.advancedFilters !== undefined) updates.advancedFilters = filters.advancedFilters;

    updateFilters(updates);
  }, [searchParams, setSearchParams, updateFilters]);

  // Clear all filters
  const handleClearFilters = () => {
    setSearchParams({}, { replace: true });
    updateFilters({
      q: '',
      assignee: '',
      queue: '',
      status: 'all',
      client_name: '',
      sort_by: 'completed_at',
      sort_order: 'desc',
      advancedFilters: {},
    });
  };

  // Check if any filters are active
  const hasActiveFilters = q || assignee || queue || status !== 'all' || clientName || 
    Object.keys(advancedFilters).length > 0;

  return (
    <div className="space-y-4">
      {/* Main Filter Row */}
      <div className="flex flex-wrap items-end gap-4">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <Label htmlFor="search">Search</Label>
          <Input
            id="search"
            placeholder="Search LC numbers, clients..."
            value={q}
            onChange={(e) => updateFilters({ q: e.target.value })}
          />
        </div>

        {/* Status Filter */}
        {resource === 'results' && (
          <div className="w-[150px]">
            <Label>Status</Label>
            <Select value={status} onValueChange={(value) => updateFilters({ status: value as any })}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="compliant">Compliant</SelectItem>
                <SelectItem value="discrepancies">With Discrepancies</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Client Name */}
        <div className="w-[200px]">
          <Label>Client Name</Label>
          <Input
            placeholder="Filter by client..."
            value={clientName}
            onChange={(e) => updateFilters({ client_name: e.target.value })}
          />
        </div>

        {/* Assignee (for jobs) */}
        {resource === 'jobs' && (
          <div className="w-[150px]">
            <Label>Assignee</Label>
            <Input
              placeholder="Filter by assignee..."
              value={assignee}
              onChange={(e) => updateFilters({ assignee: e.target.value })}
            />
          </div>
        )}

        {/* Queue (for jobs) */}
        {resource === 'jobs' && (
          <div className="w-[150px]">
            <Label>Queue</Label>
            <Select value={queue} onValueChange={(value) => updateFilters({ queue: value })}>
              <SelectTrigger>
                <SelectValue placeholder="All Queues" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="">All Queues</SelectItem>
                <SelectItem value="high_priority">High Priority</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="low_priority">Low Priority</SelectItem>
              </SelectContent>
            </Select>
          </div>
        )}

        {/* Date Range */}
        <div className="w-[150px]">
          <Label>Date Range</Label>
          <Select value={dateRange} onValueChange={(value) => {
            const newParams = new URLSearchParams(searchParams);
            newParams.set('date_range', value);
            setSearchParams(newParams, { replace: true });
          }}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Last 7 days</SelectItem>
              <SelectItem value="30">Last 30 days</SelectItem>
              <SelectItem value="90">Last 90 days</SelectItem>
              <SelectItem value="180">Last 180 days</SelectItem>
              <SelectItem value="365">Last year</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Sort */}
        <div className="w-[150px]">
          <Label>Sort By</Label>
          <Select value={sortBy} onValueChange={(value) => updateFilters({ sort_by: value as any })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="completed_at">Date</SelectItem>
              <SelectItem value="compliance_score">Score</SelectItem>
              <SelectItem value="discrepancy_count">Discrepancies</SelectItem>
              <SelectItem value="client_name">Client</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-[100px]">
          <Label>Order</Label>
          <Select value={sortOrder} onValueChange={(value) => updateFilters({ sort_order: value as any })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="desc">Desc</SelectItem>
              <SelectItem value="asc">Asc</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Actions */}
        <div className="flex items-end gap-2">
          {/* Saved Views */}
          <SavedViewsManager
            resource={resource}
            currentFilters={currentFilters}
            onLoadView={handleLoadView}
          />

          {/* Clear Filters */}
          {hasActiveFilters && (
            <Button variant="outline" size="sm" onClick={handleClearFilters}>
              <X className="h-4 w-4 mr-2" />
              Clear
            </Button>
          )}

          {/* Export Buttons */}
          {onExportCSV && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportCSV}
              disabled={exportLoading}
            >
              <Download className="h-4 w-4 mr-2" />
              CSV
            </Button>
          )}
          {onExportPDF && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportPDF}
              disabled={exportLoading}
            >
              <FileText className="h-4 w-4 mr-2" />
              PDF
            </Button>
          )}
        </div>
      </div>

      {/* Advanced Filters */}
      {showAdvancedFilters && (
        <Collapsible open={isAdvancedOpen} onOpenChange={setIsAdvancedOpen}>
          <CollapsibleTrigger asChild>
            <Button variant="outline" className="w-full">
              {isAdvancedOpen ? (
                <>
                  <ChevronUp className="w-4 h-4 mr-2" />
                  Hide Advanced Filters
                </>
              ) : (
                <>
                  <ChevronDown className="w-4 h-4 mr-2" />
                  Show Advanced Filters
                </>
              )}
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent className="mt-4">
            <AdvancedFilters
              filters={advancedFilters}
              onFiltersChange={(newFilters) => updateFilters({ advancedFilters: newFilters })}
            />
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  );
}

