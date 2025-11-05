/**
 * UsageTable component - displays usage records with filtering and pagination
 */

import React, { useState } from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  ChevronLeft,
  ChevronRight,
  CalendarIcon,
  Filter,
  Download,
  Search,
  CheckCircle,
  RefreshCw,
  Upload,
  Package
} from 'lucide-react';
import { format } from 'date-fns';
// Inline cn function to avoid import/bundling issues
function cn(...classes: (string | undefined | null | boolean | Record<string, boolean>)[]): string {
  return classes
    .filter(Boolean)
    .map((cls) => {
      if (typeof cls === 'string') return cls;
      if (typeof cls === 'object' && cls !== null) {
        return Object.entries(cls)
          .filter(([_, val]) => val)
          .map(([key]) => key)
          .join(' ');
      }
      return '';
    })
    .filter(Boolean)
    .join(' ');
}
;
import { formatCurrency } from '@/types/billing';
import { useUsageRecords, useExportUsageData } from '@/hooks/useBilling';
import type { UsageRecordsFilters, UsageRecord } from '@/types/billing';

interface UsageTableProps {
  className?: string;
  initialFilters?: UsageRecordsFilters;
  onRowClick?: (record: UsageRecord) => void;
  showExport?: boolean;
}

export function UsageTable({
  className,
  initialFilters = {},
  onRowClick,
  showExport = true
}: UsageTableProps) {
  const [filters, setFilters] = useState<UsageRecordsFilters>({
    page: 1,
    per_page: 25,
    ...initialFilters
  });

  const [dateRange, setDateRange] = useState<{
    start?: Date;
    end?: Date;
  }>({});

  const { data: usageData, isLoading, error, refetch } = useUsageRecords(filters);
  const exportMutation = useExportUsageData();

  const getActionIcon = (action: string) => {
    switch (action.toLowerCase()) {
      case 'per_check':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'recheck':
        return <RefreshCw className="h-4 w-4 text-blue-600" />;
      case 'import_draft':
        return <Upload className="h-4 w-4 text-purple-600" />;
      case 'import_bundle':
        return <Package className="h-4 w-4 text-orange-600" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-600" />;
    }
  };

  const getActionDisplay = (action: string) => {
    switch (action.toLowerCase()) {
      case 'per_check':
        return 'LC Validation';
      case 'recheck':
        return 'Re-check';
      case 'import_draft':
        return 'Import Draft';
      case 'import_bundle':
        return 'Import Bundle';
      default:
        return action.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    }
  };

  const getActionColor = (action: string) => {
    switch (action.toLowerCase()) {
      case 'per_check':
        return 'bg-green-100 text-green-800';
      case 'recheck':
        return 'bg-blue-100 text-blue-800';
      case 'import_draft':
        return 'bg-purple-100 text-purple-800';
      case 'import_bundle':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleFilterChange = (key: keyof UsageRecordsFilters, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: key !== 'page' ? 1 : value // Reset to page 1 when changing other filters
    }));
  };

  const handleDateRangeChange = () => {
    setFilters(prev => ({
      ...prev,
      start_date: dateRange.start ? format(dateRange.start, 'yyyy-MM-dd') : undefined,
      end_date: dateRange.end ? format(dateRange.end, 'yyyy-MM-dd') : undefined,
      page: 1
    }));
  };

  const handleClearFilters = () => {
    setFilters({ page: 1, per_page: 25 });
    setDateRange({});
  };

  const handleExport = () => {
    exportMutation.mutate(filters);
  };

  const handlePageChange = (page: number) => {
    handleFilterChange('page', page);
  };

  const totalPages = usageData ? Math.ceil(usageData.total / (filters.per_page || 25)) : 0;
  const currentPage = filters.page || 1;

  if (error) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center py-8">
          <p className="text-sm text-muted-foreground">
            Error loading usage data. Please try again.
          </p>
          <Button variant="outline" onClick={() => refetch()} className="mt-2">
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <CardTitle className="flex items-center gap-2">
            Usage Records
            {usageData && (
              <Badge variant="secondary">
                {usageData.total.toLocaleString()} total
              </Badge>
            )}
          </CardTitle>

          {showExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={exportMutation.isPending}
              className="gap-2"
            >
              <Download className="h-4 w-4" />
              {exportMutation.isPending ? 'Exporting...' : 'Export CSV'}
            </Button>
          )}
        </div>

        {/* Filters */}
        <div className="flex flex-col lg:flex-row gap-4">
          {/* Search by action */}
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-2 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search actions..."
                value={filters.action || ''}
                onChange={(e) => handleFilterChange('action', e.target.value || undefined)}
                className="pl-8"
              />
            </div>
          </div>

          {/* Date range picker */}
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className="w-full lg:w-auto gap-2"
              >
                <CalendarIcon className="h-4 w-4" />
                {dateRange.start ? (
                  dateRange.end ? (
                    <>
                      {format(dateRange.start, 'LLL dd, y')} -{' '}
                      {format(dateRange.end, 'LLL dd, y')}
                    </>
                  ) : (
                    format(dateRange.start, 'LLL dd, y')
                  )
                ) : (
                  'Pick a date range'
                )}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                initialFocus
                mode="range"
                defaultMonth={dateRange.start}
                selected={{
                  from: dateRange.start,
                  to: dateRange.end
                }}
                onSelect={(range) => {
                  setDateRange({
                    start: range?.from,
                    end: range?.to
                  });
                }}
                numberOfMonths={2}
              />
              <div className="p-3 border-t">
                <Button
                  onClick={handleDateRangeChange}
                  className="w-full"
                  size="sm"
                >
                  Apply Date Range
                </Button>
              </div>
            </PopoverContent>
          </Popover>

          {/* Per page selector */}
          <Select
            value={filters.per_page?.toString() || '25'}
            onValueChange={(value) => handleFilterChange('per_page', parseInt(value))}
          >
            <SelectTrigger className="w-full lg:w-auto">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">10 per page</SelectItem>
              <SelectItem value="25">25 per page</SelectItem>
              <SelectItem value="50">50 per page</SelectItem>
              <SelectItem value="100">100 per page</SelectItem>
            </SelectContent>
          </Select>

          {/* Clear filters */}
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearFilters}
            className="gap-2"
          >
            <Filter className="h-4 w-4" />
            Clear
          </Button>
        </div>
      </CardHeader>

      <CardContent>
        {isLoading ? (
          <div className="space-y-3">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-4">
                <div className="w-8 h-8 bg-muted rounded animate-pulse" />
                <div className="space-y-2 flex-1">
                  <div className="h-4 bg-muted rounded animate-pulse" />
                  <div className="h-3 bg-muted rounded animate-pulse w-2/3" />
                </div>
                <div className="w-20 h-4 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        ) : usageData?.records.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground">
              No usage records found for the selected filters.
            </p>
          </div>
        ) : (
          <>
            {/* Table */}
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Action</TableHead>
                    <TableHead>Date & Time</TableHead>
                    <TableHead>Cost</TableHead>
                    <TableHead className="w-[100px]">Session</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {usageData?.records.map((record) => (
                    <TableRow
                      key={record.id}
                      className={cn(
                        'cursor-pointer hover:bg-muted/50',
                        onRowClick && 'cursor-pointer'
                      )}
                      onClick={() => onRowClick?.(record)}
                    >
                      <TableCell>
                        <div className="flex items-center space-x-3">
                          {getActionIcon(record.action)}
                          <div>
                            <Badge
                              variant="secondary"
                              className={getActionColor(record.action)}
                            >
                              {getActionDisplay(record.action)}
                            </Badge>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {format(new Date(record.created_at), 'MMM dd, yyyy')}
                          </div>
                          <div className="text-sm text-muted-foreground">
                            {format(new Date(record.created_at), 'HH:mm:ss')}
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="font-medium">
                          {formatCurrency(record.cost)}
                        </div>
                      </TableCell>
                      <TableCell>
                        {record.session_id ? (
                          <Badge variant="outline" className="text-xs">
                            {record.session_id.slice(-8)}
                          </Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between pt-4">
                <div className="text-sm text-muted-foreground">
                  Showing {((currentPage - 1) * (filters.per_page || 25)) + 1} to{' '}
                  {Math.min(currentPage * (filters.per_page || 25), usageData?.total || 0)} of{' '}
                  {usageData?.total || 0} results
                </div>

                <div className="flex items-center space-x-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage - 1)}
                    disabled={currentPage === 1}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>

                  <div className="flex items-center space-x-1">
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const page = i + 1;
                      return (
                        <Button
                          key={page}
                          variant={currentPage === page ? 'default' : 'outline'}
                          size="sm"
                          onClick={() => handlePageChange(page)}
                          className="w-8 h-8 p-0"
                        >
                          {page}
                        </Button>
                      );
                    })}
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handlePageChange(currentPage + 1)}
                    disabled={currentPage === totalPages}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

// Compact version for dashboard overview
export function UsageTableCompact({
  className,
  maxRows = 5
}: {
  className?: string;
  maxRows?: number;
}) {
  const { data: usageData, isLoading } = useUsageRecords({
    page: 1,
    per_page: maxRows
  });

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Recent Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="flex items-center space-x-3">
                <div className="w-6 h-6 bg-muted rounded animate-pulse" />
                <div className="flex-1 space-y-1">
                  <div className="h-3 bg-muted rounded animate-pulse" />
                  <div className="h-2 bg-muted rounded animate-pulse w-2/3" />
                </div>
                <div className="w-16 h-3 bg-muted rounded animate-pulse" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!usageData?.records.length) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Recent Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-4">
            No usage records found
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Recent Usage</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {usageData.records.slice(0, maxRows).map((record) => (
            <div key={record.id} className="flex items-center space-x-3">
              <div className="p-1 bg-muted rounded">
                {getActionIcon(record.action)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">
                  {getActionDisplay(record.action)}
                </div>
                <div className="text-xs text-muted-foreground">
                  {format(new Date(record.created_at), 'MMM dd, HH:mm')}
                </div>
              </div>
              <div className="text-sm font-medium">
                {formatCurrency(record.cost)}
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  function getActionIcon(action: string) {
    switch (action.toLowerCase()) {
      case 'per_check':
        return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'recheck':
        return <RefreshCw className="h-4 w-4 text-blue-600" />;
      case 'import_draft':
        return <Upload className="h-4 w-4 text-purple-600" />;
      case 'import_bundle':
        return <Package className="h-4 w-4 text-orange-600" />;
      default:
        return <CheckCircle className="h-4 w-4 text-gray-600" />;
    }
  }

  function getActionDisplay(action: string) {
    switch (action.toLowerCase()) {
      case 'per_check':
        return 'LC Validation';
      case 'recheck':
        return 'Re-check';
      case 'import_draft':
        return 'Import Draft';
      case 'import_bundle':
        return 'Import Bundle';
      default:
        return action.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase());
    }
  }
}