/**
 * TypeScript types for governance and approval workflows
 */

// Governance action types
export enum GovernanceActionType {
  ROLE_CHANGE = 'ROLE_CHANGE',
  BILLING_OVERRIDE = 'BILLING_OVERRIDE',
  QUOTA_OVERRIDE = 'QUOTA_OVERRIDE',
  PLAN_DOWNGRADE = 'PLAN_DOWNGRADE',
  INVOICE_DELETION = 'INVOICE_DELETION',
  COMPLIANCE_REPORT_EXPORT = 'COMPLIANCE_REPORT_EXPORT',
  SYSTEM_CONFIGURATION = 'SYSTEM_CONFIGURATION',
  USER_SUSPENSION = 'USER_SUSPENSION',
  COMPANY_DELETION = 'COMPANY_DELETION',
  PAYMENT_REFUND = 'PAYMENT_REFUND',
  AUDIT_LOG_ACCESS = 'AUDIT_LOG_ACCESS',
  EMERGENCY_ACCESS = 'EMERGENCY_ACCESS'
}

export enum ApprovalStatus {
  PENDING = 'PENDING',
  APPROVED = 'APPROVED',
  REJECTED = 'REJECTED',
  CANCELLED = 'CANCELLED',
  EXPIRED = 'EXPIRED',
  EXECUTED = 'EXECUTED'
}

export enum ApprovalPriority {
  LOW = 'LOW',
  NORMAL = 'NORMAL',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
  EMERGENCY = 'EMERGENCY'
}

export enum RiskLevel {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL'
}

// Core governance interfaces
export interface GovernanceAction {
  id: string;
  type: GovernanceActionType;
  title: string;
  description: string;
  justification: string;
  requester_id: string;
  requester_name: string;
  target_resource_id?: string;
  target_resource_type?: string;
  risk_level: RiskLevel;
  priority: ApprovalPriority;
  requires_four_eyes: boolean;
  requires_approval: boolean;
  approval_count_required: number;
  current_approval_count: number;
  status: ApprovalStatus;
  requested_at: string;
  expires_at?: string;
  executed_at?: string;
  cancelled_at?: string;
  metadata: Record<string, any>;
  approvals: Approval[];
  audit_trail: AuditEntry[];
}

export interface Approval {
  id: string;
  action_id: string;
  approver_id: string;
  approver_name: string;
  approver_role: string;
  status: 'APPROVED' | 'REJECTED';
  comments?: string;
  approved_at: string;
  ip_address?: string;
  user_agent?: string;
}

export interface AuditEntry {
  id: string;
  action_id: string;
  event_type: string;
  description: string;
  actor_id: string;
  actor_name: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

// Delegation system
export interface RoleDelegation {
  id: string;
  delegator_id: string;
  delegator_name: string;
  delegatee_id: string;
  delegatee_name: string;
  delegated_role: string;
  delegated_permissions: string[];
  reason: string;
  starts_at: string;
  expires_at: string;
  is_active: boolean;
  created_at: string;
  revoked_at?: string;
  revoked_by?: string;
  revocation_reason?: string;
}

// Approval policies and rules
export interface ApprovalPolicy {
  id: string;
  name: string;
  description: string;
  action_types: GovernanceActionType[];
  conditions: PolicyCondition[];
  approval_requirements: ApprovalRequirement[];
  enabled: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface PolicyCondition {
  field: string;
  operator: 'equals' | 'contains' | 'greater_than' | 'less_than' | 'in' | 'not_in';
  value: any;
  logical_operator?: 'AND' | 'OR';
}

export interface ApprovalRequirement {
  min_approvals: number;
  required_roles: string[];
  excluded_roles?: string[];
  exclude_requester: boolean;
  same_company_only?: boolean;
  time_limit_hours?: number;
}

// Governance settings
export interface GovernanceSettings {
  four_eyes_enabled: boolean;
  audit_approvals_enabled: boolean;
  delegation_enabled: boolean;
  max_delegation_hours: number;
  emergency_access_enabled: boolean;
  approval_timeout_hours: number;
  auto_rejection_enabled: boolean;
  notification_settings: GovernanceNotificationSettings;
  risk_thresholds: RiskThresholds;
}

export interface GovernanceNotificationSettings {
  notify_on_request: boolean;
  notify_on_approval: boolean;
  notify_on_rejection: boolean;
  notify_on_expiration: boolean;
  escalation_enabled: boolean;
  escalation_timeout_hours: number;
  notification_channels: string[];
}

export interface RiskThresholds {
  low_threshold: number;
  medium_threshold: number;
  high_threshold: number;
  auto_approve_low_risk: boolean;
  require_four_eyes_high_risk: boolean;
}

// API request/response types
export interface CreateGovernanceActionRequest {
  type: GovernanceActionType;
  title: string;
  description: string;
  justification: string;
  target_resource_id?: string;
  target_resource_type?: string;
  priority?: ApprovalPriority;
  metadata?: Record<string, any>;
}

export interface ApproveActionRequest {
  action_id: string;
  comments?: string;
}

export interface RejectActionRequest {
  action_id: string;
  reason: string;
  comments?: string;
}

export interface CreateDelegationRequest {
  delegatee_id: string;
  delegated_role: string;
  delegated_permissions?: string[];
  reason: string;
  duration_hours: number;
}

export interface GovernanceFilters {
  status?: ApprovalStatus;
  type?: GovernanceActionType;
  priority?: ApprovalPriority;
  risk_level?: RiskLevel;
  requester_id?: string;
  approver_id?: string;
  start_date?: string;
  end_date?: string;
  requires_my_approval?: boolean;
  page?: number;
  per_page?: number;
}

export interface GovernanceStats {
  total_actions: number;
  pending_actions: number;
  approved_actions: number;
  rejected_actions: number;
  expired_actions: number;
  average_approval_time: number;
  four_eyes_compliance_rate: number;
  by_type: Record<GovernanceActionType, number>;
  by_risk_level: Record<RiskLevel, number>;
  recent_activity: GovernanceActivity[];
}

export interface GovernanceActivity {
  timestamp: string;
  action_type: GovernanceActionType;
  status: ApprovalStatus;
  count: number;
}

// Emergency access
export interface EmergencyAccess {
  id: string;
  requester_id: string;
  requester_name: string;
  reason: string;
  requested_permissions: string[];
  granted_permissions: string[];
  justification: string;
  status: 'PENDING' | 'GRANTED' | 'DENIED' | 'EXPIRED' | 'REVOKED';
  granted_at?: string;
  expires_at?: string;
  granted_by?: string;
  granted_by_name?: string;
  revoked_at?: string;
  revoked_by?: string;
  revoked_reason?: string;
  created_at: string;
}

// Compliance reporting
export interface ComplianceReport {
  id: string;
  report_type: string;
  period_start: string;
  period_end: string;
  generated_by: string;
  generated_at: string;
  approval_required: boolean;
  approved_by?: string;
  approved_at?: string;
  governance_actions_count: number;
  four_eyes_compliance_rate: number;
  policy_violations: PolicyViolation[];
  recommendations: string[];
}

export interface PolicyViolation {
  id: string;
  policy_id: string;
  policy_name: string;
  violation_type: string;
  description: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  occurred_at: string;
  resolved_at?: string;
  resolution_notes?: string;
}

// Utility functions
export function getActionRiskLevel(action: GovernanceAction): RiskLevel {
  // Calculate risk based on action type and metadata
  switch (action.type) {
    case GovernanceActionType.COMPANY_DELETION:
    case GovernanceActionType.SYSTEM_CONFIGURATION:
      return RiskLevel.CRITICAL;
    case GovernanceActionType.ROLE_CHANGE:
    case GovernanceActionType.USER_SUSPENSION:
    case GovernanceActionType.PAYMENT_REFUND:
      return RiskLevel.HIGH;
    case GovernanceActionType.BILLING_OVERRIDE:
    case GovernanceActionType.QUOTA_OVERRIDE:
    case GovernanceActionType.PLAN_DOWNGRADE:
      return RiskLevel.MEDIUM;
    default:
      return RiskLevel.LOW;
  }
}

export function requiresFourEyes(action: GovernanceAction): boolean {
  return action.risk_level === RiskLevel.HIGH ||
         action.risk_level === RiskLevel.CRITICAL ||
         action.requires_four_eyes;
}

export function getApprovalStatusColor(status: ApprovalStatus): string {
  switch (status) {
    case ApprovalStatus.PENDING:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case ApprovalStatus.APPROVED:
    case ApprovalStatus.EXECUTED:
      return 'bg-green-100 text-green-800 border-green-200';
    case ApprovalStatus.REJECTED:
    case ApprovalStatus.CANCELLED:
      return 'bg-red-100 text-red-800 border-red-200';
    case ApprovalStatus.EXPIRED:
      return 'bg-gray-100 text-gray-800 border-gray-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function getRiskLevelColor(risk: RiskLevel): string {
  switch (risk) {
    case RiskLevel.CRITICAL:
      return 'bg-red-100 text-red-800 border-red-200';
    case RiskLevel.HIGH:
      return 'bg-orange-100 text-orange-800 border-orange-200';
    case RiskLevel.MEDIUM:
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    case RiskLevel.LOW:
      return 'bg-green-100 text-green-800 border-green-200';
    default:
      return 'bg-gray-100 text-gray-800 border-gray-200';
  }
}

export function formatActionType(type: GovernanceActionType): string {
  switch (type) {
    case GovernanceActionType.ROLE_CHANGE: return 'Role Change';
    case GovernanceActionType.BILLING_OVERRIDE: return 'Billing Override';
    case GovernanceActionType.QUOTA_OVERRIDE: return 'Quota Override';
    case GovernanceActionType.PLAN_DOWNGRADE: return 'Plan Downgrade';
    case GovernanceActionType.INVOICE_DELETION: return 'Invoice Deletion';
    case GovernanceActionType.COMPLIANCE_REPORT_EXPORT: return 'Compliance Report Export';
    case GovernanceActionType.SYSTEM_CONFIGURATION: return 'System Configuration';
    case GovernanceActionType.USER_SUSPENSION: return 'User Suspension';
    case GovernanceActionType.COMPANY_DELETION: return 'Company Deletion';
    case GovernanceActionType.PAYMENT_REFUND: return 'Payment Refund';
    case GovernanceActionType.AUDIT_LOG_ACCESS: return 'Audit Log Access';
    case GovernanceActionType.EMERGENCY_ACCESS: return 'Emergency Access';
    default: return type;
  }
}

export function canApproveAction(action: GovernanceAction, userId: string, userRole: string): boolean {
  // Cannot approve own request
  if (action.requester_id === userId) {
    return false;
  }

  // Check if already approved by this user
  const existingApproval = action.approvals.find(a => a.approver_id === userId);
  if (existingApproval) {
    return false;
  }

  // Check if action is in pending status
  if (action.status !== ApprovalStatus.PENDING) {
    return false;
  }

  // Check role-based permissions (this would be more complex in real implementation)
  const allowedRoles = ['ADMIN', 'BANK', 'COMPANY_ADMIN'];
  return allowedRoles.includes(userRole);
}

export function getTimeRemaining(expiresAt: string): string {
  const now = new Date();
  const expiry = new Date(expiresAt);
  const diffMs = expiry.getTime() - now.getTime();

  if (diffMs <= 0) {
    return 'Expired';
  }

  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffMinutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

  if (diffHours > 24) {
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ${diffHours % 24}h`;
  } else if (diffHours > 0) {
    return `${diffHours}h ${diffMinutes}m`;
  } else {
    return `${diffMinutes}m`;
  }
}

export function calculateComplianceScore(actions: GovernanceAction[]): number {
  if (actions.length === 0) return 100;

  const highRiskActions = actions.filter(a =>
    a.risk_level === RiskLevel.HIGH || a.risk_level === RiskLevel.CRITICAL
  );

  const compliantActions = highRiskActions.filter(a =>
    a.requires_four_eyes && a.current_approval_count >= 2
  );

  return (compliantActions.length / highRiskActions.length) * 100;
}