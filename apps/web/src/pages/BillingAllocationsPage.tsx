/**
 * Billing Allocations Page - manage budgets and chargebacks by SME/branch
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import {
  PieChart,
  Download,
  Edit,
  AlertTriangle,
  Building2,
  Users,
  DollarSign
} from 'lucide-react';
import { useBankAuth } from '@/lib/bank/auth';
import { format } from 'date-fns';

// Billing components
import { BillingNav, BillingBreadcrumb } from '@/components/billing/BillingNav';
import { billingApi } from '@/api/billing';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Allocation, AllocationUpdate } from '@/types/billing';
import { formatCurrency } from '@/types/billing';
import { toast } from 'sonner';

export function BillingAllocationsPage({ onTabChange }: { onTabChange?: (tab: string) => void }) {
  const { user } = useBankAuth();
  const isBankAdmin = user?.role === 'bank_admin';
  const [filters, setFilters] = useState({ page: 1, per_page: 20 });
  const [editingAllocation, setEditingAllocation] = useState<Allocation | null>(null);
  const [showEditModal, setShowEditModal] = useState(false);
  const queryClient = useQueryClient();

  const { data: allocationsData, isLoading } = useQuery({
    queryKey: ['allocations', filters],
    queryFn: () => billingApi.getAllocations(filters),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AllocationUpdate }) =>
      billingApi.updateAllocation(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['allocations'] });
      toast.success('Allocation updated successfully');
      setShowEditModal(false);
      setEditingAllocation(null);
    },
    onError: () => {
      toast.error('Failed to update allocation');
    },
  });

  const handleEdit = (allocation: Allocation) => {
    if (!isBankAdmin) {
      toast.error('Only bank administrators can edit allocations');
      return;
    }
    setEditingAllocation(allocation);
    setShowEditModal(true);
  };

  const handleSave = () => {
    if (!editingAllocation) return;
    const formData = new FormData(document.getElementById('allocation-form') as HTMLFormElement);
    const data: AllocationUpdate = {
      budget_limit: formData.get('budget_limit') ? parseFloat(formData.get('budget_limit') as string) : null,
      quota_limit: formData.get('quota_limit') ? parseInt(formData.get('quota_limit') as string) : null,
      alerts_enabled: formData.get('alerts_enabled') === 'on',
      alert_threshold_percent: formData.get('alert_threshold_percent') ? parseInt(formData.get('alert_threshold_percent') as string) : 80,
    };
    updateMutation.mutate({ id: editingAllocation.id, data });
  };

  const handleExport = () => {
    // Export CSV functionality
    const csv = [
      ['Client', 'Branch', 'Product', 'Budget Limit', 'Quota Limit', 'Usage', 'Cost', 'Remaining Budget'].join(','),
      ...(allocationsData?.allocations || []).map(a => [
        a.client_name || 'Bank-wide',
        a.branch_name || 'All',
        a.product || 'All',
        a.budget_limit || 'Unlimited',
        a.quota_limit || 'Unlimited',
        a.usage_current_period,
        a.usage_cost_current_period,
        a.remaining_budget || 'N/A',
      ].join(','))
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `allocations-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const getUsagePercentage = (allocation: Allocation) => {
    if (!allocation.budget_limit) return 0;
    return (allocation.usage_cost_current_period / allocation.budget_limit) * 100;
  };

  const getUsageColor = (percentage: number, threshold: number) => {
    if (percentage >= threshold) return 'text-red-600 bg-red-100';
    if (percentage >= threshold * 0.8) return 'text-yellow-600 bg-yellow-100';
    return 'text-green-600 bg-green-100';
  };

  return (
    <div className="container mx-auto p-6 space-y-6">
      {/* Breadcrumb */}
      <BillingBreadcrumb />

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Allocations</h1>
          <p className="text-muted-foreground">
            Manage budgets and chargebacks by SME/client, branch, and product
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button variant="outline" onClick={handleExport} className="gap-2">
            <Download className="h-4 w-4" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Navigation */}
      <BillingNav currentTab="allocations" onTabChange={onTabChange} mode="bank" hideUpgrade />

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Allocations</CardTitle>
            <PieChart className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{allocationsData?.total || 0}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Budget</CardTitle>
            <DollarSign className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(
                (allocationsData?.allocations || []).reduce((sum, a) => sum + (a.budget_limit || 0), 0)
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Usage</CardTitle>
            <Users className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {formatCurrency(
                (allocationsData?.allocations || []).reduce((sum, a) => sum + a.usage_cost_current_period, 0)
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Alerts Enabled</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {(allocationsData?.allocations || []).filter(a => a.alerts_enabled).length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Allocations Table */}
      <Card>
        <CardHeader>
          <CardTitle>Allocations</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : allocationsData?.allocations.length === 0 ? (
            <div className="text-center py-8">
              <Building2 className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-sm text-muted-foreground">No allocations found.</p>
            </div>
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Client</TableHead>
                    <TableHead>Branch</TableHead>
                    <TableHead>Product</TableHead>
                    <TableHead>Budget Limit</TableHead>
                    <TableHead>Quota Limit</TableHead>
                    <TableHead>Usage</TableHead>
                    <TableHead>Cost</TableHead>
                    <TableHead>Remaining</TableHead>
                    <TableHead>Alerts</TableHead>
                    <TableHead className="w-[100px]">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allocationsData?.allocations.map((allocation) => {
                    const usagePercent = getUsagePercentage(allocation);
                    return (
                      <TableRow key={allocation.id}>
                        <TableCell className="font-medium">
                          {allocation.client_name || 'Bank-wide'}
                        </TableCell>
                        <TableCell>{allocation.branch_name || 'All'}</TableCell>
                        <TableCell>{allocation.product || 'All'}</TableCell>
                        <TableCell>
                          {allocation.budget_limit 
                            ? formatCurrency(allocation.budget_limit)
                            : 'Unlimited'}
                        </TableCell>
                        <TableCell>
                          {allocation.quota_limit 
                            ? allocation.quota_limit.toLocaleString()
                            : 'Unlimited'}
                        </TableCell>
                        <TableCell>
                          <div className="space-y-1">
                            <div className="text-sm font-medium">
                              {allocation.usage_current_period.toLocaleString()}
                            </div>
                            {allocation.budget_limit && (
                              <div className="text-xs text-muted-foreground">
                                {usagePercent.toFixed(1)}% of budget
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="secondary"
                            className={getUsageColor(usagePercent, allocation.alert_threshold_percent)}
                          >
                            {formatCurrency(allocation.usage_cost_current_period)}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          {allocation.remaining_budget !== null
                            ? formatCurrency(allocation.remaining_budget)
                            : 'N/A'}
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center space-x-2">
                            <Switch
                              checked={allocation.alerts_enabled}
                              disabled
                              className="pointer-events-none"
                            />
                            <span className="text-xs text-muted-foreground">
                              {allocation.alert_threshold_percent}%
                            </span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(allocation)}
                            className="gap-2"
                          >
                            <Edit className="h-4 w-4" />
                            Edit
                          </Button>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Edit Allocation Modal */}
      <Dialog open={showEditModal} onOpenChange={setShowEditModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit Allocation</DialogTitle>
            <DialogDescription>
              Update budget limits, quota, and alert settings for this allocation.
            </DialogDescription>
          </DialogHeader>
          {editingAllocation && (
            <form id="allocation-form" className="space-y-4">
              <div className="space-y-2">
                <Label>Client</Label>
                <div className="text-sm text-muted-foreground">
                  {editingAllocation.client_name || 'Bank-wide'}
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="budget_limit">Budget Limit</Label>
                <Input
                  id="budget_limit"
                  name="budget_limit"
                  type="number"
                  defaultValue={editingAllocation.budget_limit || ''}
                  placeholder="Leave empty for unlimited"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="quota_limit">Quota Limit</Label>
                <Input
                  id="quota_limit"
                  name="quota_limit"
                  type="number"
                  defaultValue={editingAllocation.quota_limit || ''}
                  placeholder="Leave empty for unlimited"
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center space-x-2">
                  <Switch
                    id="alerts_enabled"
                    name="alerts_enabled"
                    defaultChecked={editingAllocation.alerts_enabled}
                  />
                  <Label htmlFor="alerts_enabled">Enable Alerts</Label>
                </div>
              </div>

              <div className="space-y-2">
                <Label htmlFor="alert_threshold_percent">Alert Threshold (%)</Label>
                <Input
                  id="alert_threshold_percent"
                  name="alert_threshold_percent"
                  type="number"
                  min="0"
                  max="100"
                  defaultValue={editingAllocation.alert_threshold_percent}
                />
              </div>
            </form>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowEditModal(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={updateMutation.isPending}>
              {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

