/**
 * Governance Panel - 4-eyes principle and audit approval workflows
 * Handles governance actions, approvals, delegations, and compliance
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Shield,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  Users,
  AlertTriangle,
  FileText,
  UserCheck,
  Settings,
  Gavel,
  History,
  TrendingUp,
  Calendar,
  Timer,
  User,
  Building
} from 'lucide-react';
import { format, formatDistanceToNow } from 'date-fns';

// Hooks and types
// TODO: Implement useGovernance hook - currently using mock data
// import {
//   useGovernanceActions,
//   useGovernanceStats,
//   useApproveAction,
//   useRejectAction,
//   useCreateGovernanceAction,
//   useRoleDelegations,
//   useCreateRoleDelegation,
//   useRevokeRoleDelegation
// } from '@/hooks/useGovernance';
import {
  GovernanceActionType,
  ApprovalStatus,
  ApprovalPriority,
  RiskLevel,
  getApprovalStatusColor,
  getRiskLevelColor,
  formatActionType,
  canApproveAction,
  getTimeRemaining,
  requiresFourEyes
} from '@/types/governance';
import type {
  GovernanceAction,
  GovernanceFilters,
  CreateGovernanceActionRequest,
  ApproveActionRequest,
  RejectActionRequest,
  CreateDelegationRequest
} from '@/types/governance';
import { useAuth } from '@/hooks/use-auth';

interface GovernancePanelProps {
  className?: string;
}

export function GovernancePanel({ className }: GovernancePanelProps) {
  const [activeTab, setActiveTab] = useState<'pending' | 'history' | 'delegations' | 'policies'>('pending');
  const [showActionModal, setShowActionModal] = useState(false);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [showRejectionDialog, setShowRejectionDialog] = useState(false);
  const [showDelegationModal, setShowDelegationModal] = useState(false);
  const [selectedAction, setSelectedAction] = useState<GovernanceAction | null>(null);
  const [approvalComments, setApprovalComments] = useState('');
  const [rejectionReason, setRejectionReason] = useState('');
  const [filters, setFilters] = useState<GovernanceFilters>({
    page: 1,
    per_page: 25
  });

  const { user } = useAuth();

  // Role-based access control
  const canManageGovernance = user?.role === 'admin' || user?.role === 'bank';

  // Queries - TODO: Replace with real hooks when useGovernance is implemented
  // Using mock data for now
  const actionsLoading = false;
  const statsLoading = false;
  const delegationsLoading = false;
  const refetchActions = () => {};

  // Mutations - TODO: Replace with real hooks when useGovernance is implemented
  const approveAction = { mutate: () => {}, isPending: false };
  const rejectAction = { mutate: () => {}, isPending: false };
  const createAction = { mutate: () => {}, isPending: false };
  const createDelegation = { mutate: () => {}, isPending: false };
  const revokeDelegation = { mutate: () => {}, isPending: false };

  // Access denied for unauthorized roles
  if (!canManageGovernance) {
    return (
      <div className={className}>
        <Card>
          <CardContent className="p-8 text-center">
            <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-muted-foreground">
              Governance management is only available to Bank and Admin users.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock data for demonstration
  const mockStats = {
    total_actions: 127,
    pending_actions: 8,
    approved_actions: 104,
    rejected_actions: 12,
    expired_actions: 3,
    average_approval_time: 4.2,
    four_eyes_compliance_rate: 96.8,
    by_type: {
      [GovernanceActionType.ROLE_CHANGE]: 35,
      [GovernanceActionType.BILLING_OVERRIDE]: 28,
      [GovernanceActionType.QUOTA_OVERRIDE]: 24,
      [GovernanceActionType.COMPLIANCE_REPORT_EXPORT]: 18,
      [GovernanceActionType.PLAN_DOWNGRADE]: 12,
      [GovernanceActionType.INVOICE_DELETION]: 8,
      [GovernanceActionType.USER_SUSPENSION]: 2
    },
    by_risk_level: {
      [RiskLevel.LOW]: 45,
      [RiskLevel.MEDIUM]: 58,
      [RiskLevel.HIGH]: 20,
      [RiskLevel.CRITICAL]: 4
    }
  };

  const mockActions = [
    {
      id: '1',
      type: GovernanceActionType.QUOTA_OVERRIDE,
      title: 'Emergency Quota Increase for ABC Ltd',
      description: 'Increase quota from 100 to 500 validations for critical project deadline',
      justification: 'Client has urgent compliance requirement for month-end processing',
      requester_id: 'user-123',
      requester_name: 'John Manager',
      target_resource_id: 'company-abc',
      target_resource_type: 'company',
      risk_level: RiskLevel.HIGH,
      priority: ApprovalPriority.HIGH,
      requires_four_eyes: true,
      requires_approval: true,
      approval_count_required: 2,
      current_approval_count: 1,
      status: ApprovalStatus.PENDING,
      requested_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
      expires_at: new Date(Date.now() + 22 * 60 * 60 * 1000).toISOString(),
      metadata: { old_quota: 100, new_quota: 500, company_name: 'ABC Ltd' },
      approvals: [
        {
          id: 'app-1',
          action_id: '1',
          approver_id: 'admin-1',
          approver_name: 'Alice Admin',
          approver_role: 'ADMIN',
          status: 'APPROVED' as const,
          comments: 'Approved for urgent compliance needs',
          approved_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString()
        }
      ],
      audit_trail: []
    },
    {
      id: '2',
      type: GovernanceActionType.COMPLIANCE_REPORT_EXPORT,
      title: 'Export Q4 Compliance Report',
      description: 'Export comprehensive compliance report for regulatory submission',
      justification: 'Required for quarterly regulatory filing with Bangladesh Bank',
      requester_id: 'bank-user-456',
      requester_name: 'Sarah Compliance',
      risk_level: RiskLevel.MEDIUM,
      priority: ApprovalPriority.NORMAL,
      requires_four_eyes: true,
      requires_approval: true,
      approval_count_required: 2,
      current_approval_count: 0,
      status: ApprovalStatus.PENDING,
      requested_at: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(),
      expires_at: new Date(Date.now() + 20 * 60 * 60 * 1000).toISOString(),
      metadata: { report_type: 'quarterly', period: 'Q4-2024' },
      approvals: [],
      audit_trail: []
    },
    {
      id: '3',
      type: GovernanceActionType.ROLE_CHANGE,
      title: 'Promote User to Company Admin',
      description: 'Elevate user permissions from Importer to Company Admin role',
      justification: 'User has demonstrated competency and business need for elevated access',
      requester_id: 'admin-789',
      requester_name: 'Bob Admin',
      target_resource_id: 'user-xyz',
      target_resource_type: 'user',
      risk_level: RiskLevel.HIGH,
      priority: ApprovalPriority.NORMAL,
      requires_four_eyes: true,
      requires_approval: true,
      approval_count_required: 2,
      current_approval_count: 2,
      status: ApprovalStatus.APPROVED,
      requested_at: new Date(Date.now() - 8 * 60 * 60 * 1000).toISOString(),
      executed_at: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(),
      metadata: { old_role: 'IMPORTER', new_role: 'COMPANY_ADMIN', user_name: 'Mike Smith' },
      approvals: [
        {
          id: 'app-2',
          action_id: '3',
          approver_id: 'admin-2',
          approver_name: 'Carol Admin',
          approver_role: 'ADMIN',
          status: 'APPROVED' as const,
          approved_at: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString()
        },
        {
          id: 'app-3',
          action_id: '3',
          approver_id: 'bank-1',
          approver_name: 'David Bank',
          approver_role: 'BANK',
          status: 'APPROVED' as const,
          approved_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString()
        }
      ],
      audit_trail: []
    }
  ];

  const mockDelegations = [
    {
      id: 'del-1',
      delegator_id: 'admin-1',
      delegator_name: 'Alice Admin',
      delegatee_id: 'user-456',
      delegatee_name: 'Bob Manager',
      delegated_role: 'BANK',
      delegated_permissions: ['approve_quota_override', 'view_compliance_reports'],
      reason: 'Temporary delegation during vacation period',
      starts_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      expires_at: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString(),
      is_active: true,
      created_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
    }
  ];

  const handleApproveAction = async (action: GovernanceAction) => {
    setSelectedAction(action);
    setShowApprovalDialog(true);
  };

  const handleRejectAction = async (action: GovernanceAction) => {
    setSelectedAction(action);
    setShowRejectionDialog(true);
  };

  const confirmApproval = async () => {
    if (!selectedAction) return;

    try {
      await approveAction.mutateAsync({
        action_id: selectedAction.id,
        comments: approvalComments
      });
      setShowApprovalDialog(false);
      setApprovalComments('');
      setSelectedAction(null);
      refetchActions();
    } catch (error) {
      console.error('Failed to approve action:', error);
    }
  };

  const confirmRejection = async () => {
    if (!selectedAction) return;

    try {
      await rejectAction.mutateAsync({
        action_id: selectedAction.id,
        reason: rejectionReason,
        comments: rejectionReason
      });
      setShowRejectionDialog(false);
      setRejectionReason('');
      setSelectedAction(null);
      refetchActions();
    } catch (error) {
      console.error('Failed to reject action:', error);
    }
  };

  const getActionIcon = (type: GovernanceActionType) => {
    switch (type) {
      case GovernanceActionType.ROLE_CHANGE: return <UserCheck className="h-4 w-4" />;
      case GovernanceActionType.BILLING_OVERRIDE: return <FileText className="h-4 w-4" />;
      case GovernanceActionType.QUOTA_OVERRIDE: return <TrendingUp className="h-4 w-4" />;
      case GovernanceActionType.COMPLIANCE_REPORT_EXPORT: return <Shield className="h-4 w-4" />;
      case GovernanceActionType.PLAN_DOWNGRADE: return <TrendingUp className="h-4 w-4 rotate-180" />;
      case GovernanceActionType.USER_SUSPENSION: return <XCircle className="h-4 w-4" />;
      case GovernanceActionType.COMPANY_DELETION: return <Building className="h-4 w-4" />;
      default: return <Gavel className="h-4 w-4" />;
    }
  };

  if (actionsLoading || statsLoading) {
    return (
      <div className={className}>
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Shield className="h-6 w-6" />
            Governance & Approvals
          </h1>
          <p className="text-muted-foreground">
            Manage 4-eyes principle, audit approvals, and role delegations
          </p>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Pending Approvals</CardTitle>
            <Clock className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-yellow-600">{mockStats.pending_actions}</div>
            <p className="text-xs text-muted-foreground">
              Require immediate attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">4-Eyes Compliance</CardTitle>
            <Eye className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mockStats.four_eyes_compliance_rate}%</div>
            <p className="text-xs text-muted-foreground">
              Last 30 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Approval Time</CardTitle>
            <Timer className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{mockStats.average_approval_time}h</div>
            <p className="text-xs text-muted-foreground">
              Average processing time
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Actions</CardTitle>
            <Gavel className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{mockStats.total_actions}</div>
            <p className="text-xs text-muted-foreground">
              This month
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="pending">Pending Approvals</TabsTrigger>
          <TabsTrigger value="history">Action History</TabsTrigger>
          <TabsTrigger value="delegations">Role Delegations</TabsTrigger>
          <TabsTrigger value="policies">Approval Policies</TabsTrigger>
        </TabsList>

        <TabsContent value="pending" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Pending Governance Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockActions
                  .filter(action => action.status === ApprovalStatus.PENDING)
                  .map((action) => (
                    <Card key={action.id} className="border-l-4 border-l-yellow-500">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start space-x-4">
                            <div className="flex-shrink-0 mt-1">
                              {getActionIcon(action.type)}
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center space-x-2 mb-2">
                                <h3 className="font-semibold">{action.title}</h3>
                                <Badge className={`text-xs ${getRiskLevelColor(action.risk_level)}`}>
                                  {action.risk_level} RISK
                                </Badge>
                                {requiresFourEyes(action) && (
                                  <Badge variant="outline" className="text-xs">
                                    4-EYES REQUIRED
                                  </Badge>
                                )}
                              </div>
                              <p className="text-sm text-muted-foreground mb-2">
                                {action.description}
                              </p>
                              <div className="text-xs text-muted-foreground">
                                <div>Requested by: {action.requester_name}</div>
                                <div>Requested: {formatDistanceToNow(new Date(action.requested_at))} ago</div>
                                <div>Expires: {action.expires_at && getTimeRemaining(action.expires_at)}</div>
                                <div>Approvals: {action.current_approval_count}/{action.approval_count_required}</div>
                              </div>
                              {action.justification && (
                                <div className="mt-2 p-2 bg-muted rounded text-xs">
                                  <strong>Justification:</strong> {action.justification}
                                </div>
                              )}
                            </div>
                          </div>
                          <div className="flex flex-col space-y-2">
                            {canApproveAction(action, user?.id || '', user?.role || '') && (
                              <>
                                <Button
                                  size="sm"
                                  onClick={() => handleApproveAction(action)}
                                  disabled={approveAction.isPending}
                                  className="gap-1"
                                >
                                  <CheckCircle className="h-3 w-3" />
                                  Approve
                                </Button>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => handleRejectAction(action)}
                                  disabled={rejectAction.isPending}
                                  className="gap-1 text-red-600 hover:text-red-700"
                                >
                                  <XCircle className="h-3 w-3" />
                                  Reject
                                </Button>
                              </>
                            )}
                          </div>
                        </div>

                        {action.approvals.length > 0 && (
                          <div className="mt-4 pt-4 border-t">
                            <div className="text-xs font-medium mb-2">Existing Approvals:</div>
                            <div className="space-y-1">
                              {action.approvals.map((approval) => (
                                <div key={approval.id} className="flex items-center space-x-2 text-xs">
                                  <CheckCircle className="h-3 w-3 text-green-600" />
                                  <span>{approval.approver_name} ({approval.approver_role})</span>
                                  <span className="text-muted-foreground">
                                    {formatDistanceToNow(new Date(approval.approved_at))} ago
                                  </span>
                                  {approval.comments && (
                                    <span className="text-muted-foreground">- {approval.comments}</span>
                                  )}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  ))}

                {mockActions.filter(action => action.status === ApprovalStatus.PENDING).length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Gavel className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <div>No pending approvals</div>
                    <div className="text-sm">All governance actions are up to date</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Action History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockActions
                  .filter(action => action.status !== ApprovalStatus.PENDING)
                  .map((action) => (
                    <div key={action.id} className="flex items-center justify-between p-4 border rounded-lg">
                      <div className="flex items-start space-x-4">
                        <div className="flex-shrink-0 mt-1">
                          {getActionIcon(action.type)}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center space-x-2 mb-1">
                            <h3 className="font-medium">{action.title}</h3>
                            <Badge className={`text-xs ${getApprovalStatusColor(action.status)}`}>
                              {action.status}
                            </Badge>
                            <Badge className={`text-xs ${getRiskLevelColor(action.risk_level)}`}>
                              {action.risk_level}
                            </Badge>
                          </div>
                          <p className="text-sm text-muted-foreground">{action.description}</p>
                          <div className="text-xs text-muted-foreground mt-1">
                            By {action.requester_name} • {format(new Date(action.requested_at), 'MMM dd, HH:mm')}
                            {action.executed_at && (
                              <span> • Executed {formatDistanceToNow(new Date(action.executed_at))} ago</span>
                            )}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-medium">
                          {action.current_approval_count}/{action.approval_count_required} approvals
                        </div>
                        {action.approvals.length > 0 && (
                          <div className="text-xs text-muted-foreground">
                            {action.approvals.map(a => a.approver_name).join(', ')}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="delegations" className="space-y-4">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Role Delegations</CardTitle>
                <Button
                  onClick={() => setShowDelegationModal(true)}
                  size="sm"
                  className="gap-2"
                >
                  <Users className="h-4 w-4" />
                  New Delegation
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockDelegations.map((delegation) => (
                  <Card key={delegation.id} className="border-l-4 border-l-blue-500">
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex items-start space-x-4">
                          <Users className="h-5 w-5 mt-1 text-blue-600" />
                          <div className="flex-1">
                            <div className="flex items-center space-x-2 mb-2">
                              <h3 className="font-medium">
                                {delegation.delegator_name} → {delegation.delegatee_name}
                              </h3>
                              <Badge variant={delegation.is_active ? 'default' : 'secondary'}>
                                {delegation.is_active ? 'Active' : 'Inactive'}
                              </Badge>
                            </div>
                            <div className="text-sm text-muted-foreground mb-2">
                              <div>Role: {delegation.delegated_role}</div>
                              <div>Permissions: {delegation.delegated_permissions.join(', ')}</div>
                              <div>Reason: {delegation.reason}</div>
                            </div>
                            <div className="text-xs text-muted-foreground">
                              <div>Started: {format(new Date(delegation.starts_at), 'MMM dd, yyyy HH:mm')}</div>
                              <div>Expires: {format(new Date(delegation.expires_at), 'MMM dd, yyyy HH:mm')}</div>
                              <div>Time remaining: {getTimeRemaining(delegation.expires_at)}</div>
                            </div>
                          </div>
                        </div>
                        {delegation.is_active && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => revokeDelegation.mutate(delegation.id)}
                            disabled={revokeDelegation.isPending}
                            className="text-red-600 hover:text-red-700"
                          >
                            Revoke
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}

                {mockDelegations.length === 0 && (
                  <div className="text-center py-8 text-muted-foreground">
                    <Users className="h-12 w-12 mx-auto mb-4 opacity-50" />
                    <div>No active delegations</div>
                    <div className="text-sm">Create a delegation to temporarily grant elevated permissions</div>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="policies" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Approval Policies</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-8 text-muted-foreground">
                <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
                <div>Policy management interface</div>
                <div className="text-sm">Configure approval requirements and governance rules</div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Approval Dialog */}
      <AlertDialog open={showApprovalDialog} onOpenChange={setShowApprovalDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Approve Governance Action</AlertDialogTitle>
            <AlertDialogDescription>
              You are about to approve "{selectedAction?.title}". This action cannot be undone.
              {selectedAction && requiresFourEyes(selectedAction) && (
                <div className="mt-2 p-2 bg-yellow-100 text-yellow-800 rounded text-sm">
                  <AlertTriangle className="h-4 w-4 inline mr-1" />
                  This is a high-risk action requiring 4-eyes principle compliance.
                </div>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="my-4">
            <Label htmlFor="approval-comments">Comments (optional)</Label>
            <Textarea
              id="approval-comments"
              value={approvalComments}
              onChange={(e) => setApprovalComments(e.target.value)}
              placeholder="Add any comments about your approval decision..."
              className="mt-1"
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmApproval}
              disabled={approveAction.isPending}
              className="bg-green-600 hover:bg-green-700"
            >
              {approveAction.isPending ? 'Approving...' : 'Approve Action'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Rejection Dialog */}
      <AlertDialog open={showRejectionDialog} onOpenChange={setShowRejectionDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject Governance Action</AlertDialogTitle>
            <AlertDialogDescription>
              You are about to reject "{selectedAction?.title}". Please provide a reason for rejection.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="my-4">
            <Label htmlFor="rejection-reason">Rejection Reason *</Label>
            <Textarea
              id="rejection-reason"
              value={rejectionReason}
              onChange={(e) => setRejectionReason(e.target.value)}
              placeholder="Explain why you are rejecting this action..."
              className="mt-1"
              required
            />
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmRejection}
              disabled={rejectAction.isPending || !rejectionReason.trim()}
              className="bg-red-600 hover:bg-red-700"
            >
              {rejectAction.isPending ? 'Rejecting...' : 'Reject Action'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Delegation Modal */}
      <DelegationModal
        open={showDelegationModal}
        onOpenChange={setShowDelegationModal}
        onSave={(data) => createDelegation.mutate(data)}
      />
    </div>
  );
}

// Delegation Modal Component
interface DelegationModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (data: CreateDelegationRequest) => void;
}

function DelegationModal({ open, onOpenChange, onSave }: DelegationModalProps) {
  const [formData, setFormData] = useState<CreateDelegationRequest>({
    delegatee_id: '',
    delegated_role: '',
    reason: '',
    duration_hours: 24
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Role Delegation</DialogTitle>
          <DialogDescription>
            Temporarily delegate role permissions to another user.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <Label htmlFor="delegatee">Delegate To (User ID)</Label>
            <Input
              id="delegatee"
              value={formData.delegatee_id}
              onChange={(e) => setFormData(prev => ({ ...prev, delegatee_id: e.target.value }))}
              placeholder="user-123"
              required
            />
          </div>

          <div>
            <Label htmlFor="role">Delegated Role</Label>
            <Select
              value={formData.delegated_role}
              onValueChange={(value) => setFormData(prev => ({ ...prev, delegated_role: value }))}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select role to delegate" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="BANK">Bank User</SelectItem>
                <SelectItem value="COMPANY_ADMIN">Company Admin</SelectItem>
                <SelectItem value="ADMIN">System Admin</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div>
            <Label htmlFor="duration">Duration (hours)</Label>
            <Input
              id="duration"
              type="number"
              value={formData.duration_hours}
              onChange={(e) => setFormData(prev => ({ ...prev, duration_hours: parseInt(e.target.value) }))}
              min="1"
              max="168"
              required
            />
          </div>

          <div>
            <Label htmlFor="reason">Reason for Delegation</Label>
            <Textarea
              id="reason"
              value={formData.reason}
              onChange={(e) => setFormData(prev => ({ ...prev, reason: e.target.value }))}
              placeholder="Explain why this delegation is necessary..."
              required
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">Create Delegation</Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}