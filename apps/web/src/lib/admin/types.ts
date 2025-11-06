import { LucideIcon } from "lucide-react";

export type AdminSection =
  | "overview"
  | "ops-monitoring"
  | "ops-jobs"
  | "ops-alerts"
  | "audit-logs"
  | "audit-approvals"
  | "audit-compliance"
  | "security-users"
  | "security-access"
  | "security-sessions"
  | "billing-plans"
  | "billing-adjustments"
  | "billing-disputes"
  | "partners-registry"
  | "partners-connectors"
  | "partners-webhooks"
  | "llm-prompts"
  | "llm-budgets"
  | "llm-evaluations"
  | "compliance-residency"
  | "compliance-retention"
  | "compliance-legal-holds"
  | "system-feature-flags"
  | "system-releases"
  | "system-settings";

export type TimeRange = "24h" | "7d" | "30d" | "90d";

export interface Pagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface PaginatedResult<T> extends Pagination {
  items: T[];
}

export interface KPIStat {
  id: string;
  label: string;
  value: string;
  change: number;
  changeLabel: string;
  changeDirection: "up" | "down" | "flat";
  icon: LucideIcon;
  href?: string;
  emphasis?: boolean;
}

export interface OpsMetric {
  id: string;
  name: string;
  value: number;
  unit?: string;
  change: number;
  trend: "up" | "down" | "stable";
  target?: number;
}

export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "scheduled";

export interface OpsJob {
  id: string;
  name: string;
  type: string;
  status: JobStatus;
  queue: string;
  retries: number;
  maxRetries: number;
  createdAt: string;
  startedAt?: string;
  completedAt?: string;
  nextRunAt?: string;
  durationMs?: number;
  metadata?: Record<string, unknown>;
}

export type AlertSeverity = "critical" | "high" | "medium" | "low" | "info";

export interface OpsAlert {
  id: string;
  title: string;
  severity: AlertSeverity;
  source: string;
  description: string;
  createdAt: string;
  acknowledgedAt?: string;
  resolvedAt?: string;
  acknowledgedBy?: string;
  tags?: string[];
  link?: string;
}

export interface AuditLogEntry {
  id: string;
  actor: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  action: string;
  entity: string;
  entityId: string;
  summary: string;
  createdAt: string;
  ip?: string;
  userAgent?: string;
  metadata?: Record<string, unknown>;
}

export type ApprovalStatus = "pending" | "approved" | "rejected" | "expired";

export interface ApprovalRequest {
  id: string;
  type: string;
  status: ApprovalStatus;
  submittedBy: string;
  submittedAt: string;
  expiresAt?: string;
  approvers: string[];
  approvedAt?: string;
  rejectedAt?: string;
  rejectionReason?: string;
  before?: Record<string, unknown>;
  after?: Record<string, unknown>;
  comments?: Array<{
    id: string;
    author: string;
    body: string;
    createdAt: string;
  }>;
}

export interface CompliancePolicyResult {
  id: string;
  name: string;
  category: string;
  status: "pass" | "fail" | "warning";
  lastRunAt: string;
  exceptions: number;
  owner: string;
  reportUrl?: string;
}

export type AdminRole = "super_admin" | "admin" | "auditor" | "support" | "billing" | "viewer";

export interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: AdminRole;
  status: "active" | "invited" | "disabled";
  invitedAt?: string;
  lastActiveAt?: string;
  mfaEnabled: boolean;
  tenants: string[];
}

export interface RoleDefinition {
  id: AdminRole;
  name: string;
  description: string;
  permissions: string[];
  editable?: boolean;
}

export type ApiKeyStatus = "active" | "rotating" | "revoked" | "expired";

export interface ApiKeyRecord {
  id: string;
  name: string;
  status: ApiKeyStatus;
  createdAt: string;
  lastUsedAt?: string;
  expiresAt?: string;
  scopes: string[];
  environment: "production" | "staging" | "development";
  hashedKey?: string;
}

export interface SessionRecord {
  id: string;
  userId: string;
  createdAt: string;
  lastSeenAt: string;
  ipAddress: string;
  location?: string;
  userAgent: string;
  device: string;
  platform: string;
  riskLevel: "low" | "medium" | "high";
}

export interface BillingPlan {
  id: string;
  name: string;
  tier: "free" | "growth" | "enterprise";
  pricePerMonth: number;
  currency: string;
  features: string[];
  limits: Record<string, string | number>;
  status: "active" | "deprecated";
}

export interface BillingAdjustment {
  id: string;
  customer: string;
  amount: number;
  currency: string;
  reason: string;
  createdAt: string;
  createdBy: string;
  status: "pending" | "posted" | "void";
}

export interface BillingDispute {
  id: string;
  customer: string;
  amount: number;
  currency: string;
  reason: string;
  openedAt: string;
  status: "open" | "won" | "lost" | "under_review";
  evidenceDueAt?: string;
  notes?: string;
}

export interface PartnerRecord {
  id: string;
  name: string;
  category: string;
  status: "active" | "inactive" | "draft";
  contactEmail: string;
  createdAt: string;
  updatedAt: string;
  markets: string[];
}

export interface ConnectorConfig {
  id: string;
  name: string;
  provider: string;
  status: "enabled" | "disabled" | "error";
  lastSyncAt?: string;
  authType: "oauth" | "api_key" | "custom";
  hasSecrets: boolean;
  config: Record<string, unknown>;
}

export interface WebhookDelivery {
  id: string;
  endpoint: string;
  status: "delivered" | "pending" | "failed";
  event: string;
  sentAt: string;
  responseCode?: number;
  retryCount: number;
  lastError?: string;
}

export interface PromptVersion {
  id: string;
  version: number;
  createdAt: string;
  createdBy: string;
  diffSummary: string;
  prompt: string;
  variables: string[];
}

export interface PromptRecord {
  id: string;
  name: string;
  description: string;
  useCase: string;
  latestVersion: PromptVersion;
  versions: PromptVersion[];
  status: "active" | "draft" | "archived";
}

export interface LLMBudget {
  id: string;
  service: string;
  provider: string;
  monthlyLimit: number;
  currency: string;
  spendingToDate: number;
  forecast: number;
  hardLimit: number;
  emails: string[];
}

export interface EvaluationRun {
  id: string;
  name: string;
  model: string;
  dataset: string;
  status: "pending" | "running" | "completed" | "failed";
  startedAt: string;
  completedAt?: string;
  metrics: {
    accuracy?: number;
    latencyMs?: number;
    cost?: number;
    score?: number;
  };
  regressions?: string[];
}

export interface ResidencyPolicy {
  id: string;
  region: string;
  storageLocation: string;
  status: "compliant" | "non_compliant" | "waived";
  lastValidatedAt: string;
  owner: string;
  notes?: string;
}

export interface RetentionSchedule {
  id: string;
  name: string;
  policy: string;
  appliesTo: string[];
  retentionDays: number;
  lastRunAt: string;
  nextRunAt: string;
  dryRunSummary?: string;
}

export interface LegalHold {
  id: string;
  name: string;
  status: "active" | "released" | "pending";
  createdAt: string;
  releasedAt?: string;
  owner: string;
  affectedObjects: number;
  notes?: string;
}

export interface FeatureFlagTargeting {
  environments: string[];
  tenants?: string[];
  percentageRollout?: number;
  conditions?: Array<{
    attribute: string;
    operator: "equals" | "not_equals" | "in" | "not_in" | "greater_than" | "less_than";
    value: string | number | boolean | string[];
  }>;
}

export interface FeatureFlagRecord {
  id: string;
  name: string;
  description: string;
  status: "enabled" | "disabled" | "scheduled";
  createdAt: string;
  updatedAt: string;
  owner: string;
  targeting: FeatureFlagTargeting;
  tags?: string[];
}

export interface ReleaseRecord {
  id: string;
  version: string;
  deployedAt: string;
  environment: string;
  author: string;
  summary: string;
  commitSha: string;
  pullRequestUrl?: string;
  status: "succeeded" | "failed" | "in_progress";
  services: Array<{
    name: string;
    previousVersion?: string;
  }>;
}

export interface AdminSettings {
  branding: {
    primaryColor: string;
    logoUrl?: string;
    supportEmail: string;
  };
  authentication: {
    passwordPolicy: string;
    mfaEnforced: boolean;
    ssoEnabled: boolean;
    sessionTimeoutMinutes: number;
  };
  notifications: {
    dailySummary: boolean;
    weeklyInsights: boolean;
    criticalAlerts: boolean;
    digestEmail: string;
  };
}

export interface AdminAuditEvent {
  id: string;
  actor: string;
  actorRole: AdminRole;
  action: string;
  section: AdminSection;
  entityId?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

export type MutationResult<T = undefined> =
  | { success: true; message?: string; data?: T }
  | { success: false; message: string };

export interface AdminService {
  getDashboardStats(range: TimeRange): Promise<KPIStat[]>;

  getOpsMetrics(range: TimeRange): Promise<OpsMetric[]>;
  listJobs(params: { page: number; pageSize: number; status?: JobStatus[]; search?: string }): Promise<PaginatedResult<OpsJob>>;
  retryJob(id: string): Promise<MutationResult>;
  cancelJob(id: string): Promise<MutationResult>;

  listAlerts(params: { page: number; pageSize: number; severity?: AlertSeverity[]; status?: "active" | "acknowledged" | "resolved" }): Promise<PaginatedResult<OpsAlert>>;
  acknowledgeAlert(id: string): Promise<MutationResult>;
  snoozeAlert(id: string, minutes: number): Promise<MutationResult>;

  listAuditLogs(params: { page: number; pageSize: number; search?: string; actor?: string; action?: string }): Promise<PaginatedResult<AuditLogEntry>>;
  listApprovalRequests(params: { status: ApprovalStatus; page: number; pageSize: number }): Promise<PaginatedResult<ApprovalRequest>>;
  resolveApproval(id: string, outcome: "approve" | "reject", reason?: string): Promise<MutationResult>;
  getComplianceSummary(): Promise<CompliancePolicyResult[]>;

  listUsers(params: { page: number; pageSize: number; search?: string; role?: AdminRole | "all" }): Promise<PaginatedResult<AdminUser>>;
  inviteUser(payload: { email: string; role: AdminRole }): Promise<MutationResult>;
  disableUser(id: string): Promise<MutationResult>;
  updateUserRole(id: string, role: AdminRole): Promise<MutationResult<AdminUser>>;
  listRoles(): Promise<RoleDefinition[]>;

  listApiKeys(params: { page: number; pageSize: number; environment?: string }): Promise<PaginatedResult<ApiKeyRecord>>;
  createApiKey(payload: { name: string; scopes: string[]; environment: string }): Promise<MutationResult<{ token: string }>>;
  rotateApiKey(id: string): Promise<MutationResult<{ token: string }>>;
  revokeApiKey(id: string): Promise<MutationResult>;

  listSessions(params: { page: number; pageSize: number; risk?: "low" | "medium" | "high" }): Promise<PaginatedResult<SessionRecord>>;
  revokeSession(id: string): Promise<MutationResult>;

  listBillingPlans(): Promise<BillingPlan[]>;
  listBillingAdjustments(params: { page: number; pageSize: number }): Promise<PaginatedResult<BillingAdjustment>>;
  addBillingAdjustment(payload: BillingAdjustment): Promise<MutationResult>;
  listBillingDisputes(params: { page: number; pageSize: number; status?: BillingDispute["status"][] }): Promise<PaginatedResult<BillingDispute>>;
  resolveDispute(id: string, outcome: "won" | "lost" | "write_off", notes?: string): Promise<MutationResult>;

  listPartners(): Promise<PartnerRecord[]>;
  setPartnerStatus(id: string, status: PartnerRecord["status"]): Promise<MutationResult>;
  listConnectors(): Promise<ConnectorConfig[]>;
  updateConnector(id: string, config: Partial<ConnectorConfig>): Promise<MutationResult>;
  listWebhookDeliveries(params: { page: number; pageSize: number; status?: WebhookDelivery["status"] }): Promise<PaginatedResult<WebhookDelivery>>;
  redeliverWebhook(id: string): Promise<MutationResult>;
  rotateWebhookSecret(id: string): Promise<MutationResult<{ secret: string }>>;

  listPrompts(): Promise<PromptRecord[]>;
  publishPromptVersion(id: string, payload: Partial<PromptVersion>): Promise<MutationResult<PromptRecord>>;
  listLLMBudgets(): Promise<LLMBudget[]>;
  updateLLMBudget(id: string, payload: Partial<LLMBudget>): Promise<MutationResult>;
  listEvaluationRuns(params: { page: number; pageSize: number; status?: EvaluationRun["status"][] }): Promise<PaginatedResult<EvaluationRun>>;

  listResidencyPolicies(): Promise<ResidencyPolicy[]>;
  listRetentionSchedules(): Promise<RetentionSchedule[]>;
  runRetentionSchedule(id: string, dryRun?: boolean): Promise<MutationResult<{ summary?: string }>>;
  listLegalHolds(): Promise<LegalHold[]>;
  createLegalHold(payload: Partial<LegalHold>): Promise<MutationResult<LegalHold>>;
  releaseLegalHold(id: string): Promise<MutationResult>;

  listFeatureFlags(): Promise<FeatureFlagRecord[]>;
  setFeatureFlagStatus(id: string, status: FeatureFlagRecord["status"]): Promise<MutationResult>;
  updateFeatureFlagTargeting(id: string, targeting: FeatureFlagTargeting): Promise<MutationResult>;

  listReleases(params: { page: number; pageSize: number; environment?: string }): Promise<PaginatedResult<ReleaseRecord>>;

  getSettings(): Promise<AdminSettings>;
  updateSettings(settings: Partial<AdminSettings>): Promise<MutationResult<AdminSettings>>;

  recordAdminAudit(event: Omit<AdminAuditEvent, "id" | "createdAt">): Promise<MutationResult>;
  listAdminAuditLog(params: { page: number; pageSize: number }): Promise<PaginatedResult<AdminAuditEvent>>;
}

