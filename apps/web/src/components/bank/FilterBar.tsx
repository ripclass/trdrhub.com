/**
 * Common FilterBar component for bank dashboard resources
 * Syncs filter state with URL query params and supports deep linking
 */

import React, { useState, useEffect, useCallback } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Search, X, Filter, ArrowUpDown } from "lucide-react";
import { BankResultsFilters, BankJobFilters } from "@/api/bank";

export type FilterBarResource = 'results' | 'jobs' | 'evidence';

export interface FilterBarProps {
  resource: FilterBarResource;
  onFiltersChange?: (filters: BankResultsFilters | BankJobFilters) => void;
  showQuickPresets?: boolean;
}

export function FilterBar({ resource, onFiltersChange, showQuickPresets = true }: FilterBarProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Filter state from URL
  const [q, setQ] = useState(searchParams.get('q') || '');
  const [clientName, setClientName] = useState(searchParams.get('client_name') || '');
  const [status, setStatus] = useState(searchParams.get('status') || 'all');
  const [sortBy, setSortBy] = useState(searchParams.get('sort_by') || (resource === 'results' ? 'completed_at' : 'created_at'));
  const [sortOrder, setSortOrder] = useState(searchParams.get('sort_order') || 'desc');
  const [assignee, setAssignee] = useState(searchParams.get('assignee') || '');
  const [queue, setQueue] = useState(searchParams.get('queue') || '');

  // Update URL when filters change
  const updateURL = useCallback((updates: Record<string, string | null>) => {
    const newParams = new URLSearchParams(searchParams);
    
    Object.entries(updates).forEach(([key, value]) => {
      if (value && value !== 'all' && value !== '') {
        newParams.set(key, value);
      } else {
        newParams.delete(key);
      }
    });

    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Sync state with URL on mount/URL changes
  useEffect(() => {
    setQ(searchParams.get('q') || '');
    setClientName(searchParams.get('client_name') || '');
    setStatus(searchParams.get('status') || 'all');
    setSortBy(searchParams.get('sort_by') || (resource === 'results' ? 'completed_at' : 'created_at'));
    setSortOrder(searchParams.get('sort_order') || 'desc');
    setAssignee(searchParams.get('assignee') || '');
    setQueue(searchParams.get('queue') || '');
  }, [searchParams, resource]);

  // Emit filter changes to parent
  useEffect(() => {
    if (!onFiltersChange) return;

    const filters: BankResultsFilters | BankJobFilters = {
      q: q || undefined,
      client_name: clientName || undefined,
      status: status !== 'all' ? status as any : undefined,
      sort_by: sortBy as any,
      sort_order: sortOrder as 'asc' | 'desc',
      assignee: assignee || undefined,
      queue: queue || undefined,
    };

    // Remove undefined values
    Object.keys(filters).forEach((key) => {
      if (filters[key as keyof typeof filters] === undefined) {
        delete filters[key as keyof typeof filters];
      }
    });

    onFiltersChange(filters);
  }, [q, clientName, status, sortBy, sortOrder, assignee, queue, onFiltersChange]);

  const handleFilterChange = (key: string, value: string) => {
    updateURL({ [key]: value });
  };

  const handleClearFilters = () => {
    setQ('');
    setClientName('');
    setStatus('all');
    setSortBy(resource === 'results' ? 'completed_at' : 'created_at');
    setSortOrder('desc');
    setAssignee('');
    setQueue('');
    
    // Clear all filter params from URL
    const newParams = new URLSearchParams();
    // Preserve non-filter params if needed
    searchParams.forEach((value, key) => {
      if (!['q', 'client_name', 'status', 'sort_by', 'sort_order', 'assignee', 'queue'].includes(key)) {
        newParams.set(key, value);
      }
    });
    setSearchParams(newParams, { replace: true });
  };

  const hasActiveFilters = q || clientName || status !== 'all' || assignee || queue;

  const quickPresets = showQuickPresets ? [
    { label: 'Last 7 Days', action: () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 7);
      updateURL({
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
      });
    }},
    { label: 'Last 30 Days', action: () => {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);
      updateURL({
        start_date: startDate.toISOString().split('T')[0],
        end_date: endDate.toISOString().split('T')[0],
      });
    }},
    { label: 'With Discrepancies', action: () => handleFilterChange('status', 'discrepancies') },
    { label: 'Compliant Only', action: () => handleFilterChange('status', 'compliant') },
  ] : [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-4">
        {/* Search */}
        <div className="flex-1 min-w-[200px]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
            <Input
              placeholder="Search LC number, client name..."
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                handleFilterChange('q', e.target.value);
              }}
              className="pl-9"
            />
          </div>
        </div>

        {/* Client Name */}
        <div className="w-[200px]">
          <Input
            placeholder="Client name"
            value={clientName}
            onChange={(e) => {
              setClientName(e.target.value);
              handleFilterChange('client_name', e.target.value);
            }}
          />
        </div>

        {/* Status */}
        <div className="w-[150px]">
          <Select value={status} onValueChange={(value) => {
            setStatus(value);
            handleFilterChange('status', value);
          }}>
            <SelectTrigger>
              <SelectValue placeholder="Status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="compliant">Compliant</SelectItem>
              <SelectItem value="discrepancies">Discrepancies</SelectItem>
              {resource === 'jobs' && (
                <>
                  <SelectItem value="created">Created</SelectItem>
                  <SelectItem value="processing">Processing</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Sort */}
        <div className="flex items-center gap-2">
          <Select value={sortBy} onValueChange={(value) => {
            setSortBy(value);
            handleFilterChange('sort_by', value);
          }}>
            <SelectTrigger className="w-[150px]">
              <SelectValue placeholder="Sort by" />
            </SelectTrigger>
            <SelectContent>
              {resource === 'results' ? (
                <>
                  <SelectItem value="completed_at">Completed At</SelectItem>
                  <SelectItem value="created_at">Created At</SelectItem>
                  <SelectItem value="compliance_score">Score</SelectItem>
                  <SelectItem value="client_name">Client</SelectItem>
                  <SelectItem value="lc_number">LC Number</SelectItem>
                </>
              ) : (
                <>
                  <SelectItem value="created_at">Created At</SelectItem>
                  <SelectItem value="completed_at">Completed At</SelectItem>
                  <SelectItem value="client_name">Client</SelectItem>
                  <SelectItem value="lc_number">LC Number</SelectItem>
                </>
              )}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            size="icon"
            onClick={() => {
              const newOrder = sortOrder === 'asc' ? 'desc' : 'asc';
              setSortOrder(newOrder);
              handleFilterChange('sort_order', newOrder);
            }}
            title={sortOrder === 'asc' ? 'Ascending' : 'Descending'}
          >
            <ArrowUpDown className="w-4 h-4" />
          </Button>
        </div>

        {/* Clear Filters */}
        {hasActiveFilters && (
          <Button variant="ghost" size="sm" onClick={handleClearFilters}>
            <X className="w-4 h-4 mr-2" />
            Clear
          </Button>
        )}
      </div>

      {/* Quick Presets */}
      {showQuickPresets && quickPresets.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm text-muted-foreground">Quick filters:</span>
          {quickPresets.map((preset, idx) => (
            <Button
              key={idx}
              variant="outline"
              size="sm"
              onClick={preset.action}
              className="h-7"
            >
              {preset.label}
            </Button>
          ))}
        </div>
      )}

      {/* Active Filter Badges */}
      {hasActiveFilters && (
        <div className="flex items-center gap-2 flex-wrap">
          <Filter className="w-4 h-4 text-muted-foreground" />
          {q && (
            <Badge variant="secondary" className="gap-1">
              Search: {q}
              <button
                onClick={() => {
                  setQ('');
                  handleFilterChange('q', '');
                }}
                className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}
          {clientName && (
            <Badge variant="secondary" className="gap-1">
              Client: {clientName}
              <button
                onClick={() => {
                  setClientName('');
                  handleFilterChange('client_name', '');
                }}
                className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}
          {status !== 'all' && (
            <Badge variant="secondary" className="gap-1">
              Status: {status}
              <button
                onClick={() => {
                  setStatus('all');
                  handleFilterChange('status', 'all');
                }}
                className="ml-1 hover:bg-destructive/20 rounded-full p-0.5"
              >
                <X className="w-3 h-3" />
              </button>
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

