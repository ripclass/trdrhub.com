import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  DollarSign,
  ShieldCheck,
  Users,
} from "lucide-react";

import {
  AdminAuditEvent,
  AdminRole,
  AdminService,
  AdminSettings,
  ApiKeyRecord,
  ApprovalRequest,
  ApprovalStatus,
  AuditLogEntry,
  BillingAdjustment,
  BillingDispute,
  BillingPlan,
  BillingSummary,
  CompliancePolicyResult,
  ConnectorConfig,
  EvaluationRun,
  FeatureFlagRecord,
  FeatureFlagTargeting,
  JobStatus,
  KPIStat,
  LegalHold,
  LLMBudget,
  MutationResult,
  OpsAlert,
  OpsMetric,
  OpsJob,
  PaginatedResult,
  PartnerRecord,
  PromptRecord,
  PromptVersion,
  ReleaseRecord,
  ResidencyPolicy,
  RetentionSchedule,
  RoleDefinition,
  RulesetRecord,
  RulesetStatus,
  RulesetUploadResult,
  ActiveRulesetResult,
  RulesetAuditLog,
  SessionRecord,
  TimeRange,
  AdminUser,
  WebhookDelivery,
} from "../../types";

type PaginateParams = {
  page: number;
  pageSize: number;
};

const clone = <T>(value: T): T => {
  if (typeof structuredClone === "function") {
    try {
      return structuredClone(value);
    } catch (error) {
      console.warn("structuredClone failed for admin mock data, falling back to manual clone", error);
    }
  }

  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "function" ? item : clone(item))) as unknown as T;
  }

  if (value && typeof value === "object") {
    const result: Record<string, unknown> = {};
    for (const [key, entry] of Object.entries(value as Record<string, unknown>)) {
      result[key] = entry && typeof entry === "object" ? clone(entry) : entry;
    }
    return result as T;
  }

  return value;
};

const randomId = () => Math.random().toString(36).slice(2, 10);

const now = () => new Date().toISOString();

function addMinutes(dateIso: string, minutes: number) {
  return new Date(new Date(dateIso).getTime() + minutes * 60_000).toISOString();
}

const PAGE_DEFAULT = { page: 1, pageSize: 10 };

const ROLES: RoleDefinition[] = [
  {
    id: "super_admin",
    name: "Super Admin",
    description: "Full platform access",
    permissions: ["*"],
  },
  {
    id: "admin",
    name: "Administrator",
    description: "Manage operations and users",
    permissions: [
      "admin:read",
      "ops:read",
      "jobs:read",
      "alerts:read",
      "alerts:write",
      "users:read",
      "users:write",
      "api_keys:read",
      "api_keys:write",
      "sessions:read",
      "sessions:write",
      "feature_flags:read",
      "feature_flags:write",
      "settings:read",
      "settings:write",
    ],
  },
  {
    id: "auditor",
    name: "Auditor",
    description: "View-only compliance and audit data",
    permissions: [
      "admin:read",
      "audit:read",
      "approvals:read",
      "compliance:read",
      "legal_holds:read",
      "releases:read",
      "settings:read",
    ],
  },
  {
    id: "support",
    name: "Support",
    description: "Assist customers with limited write access",
    permissions: [
      "admin:read",
      "ops:read",
      "jobs:read",
      "jobs:write",
      "alerts:read",
      "alerts:write",
      "sessions:read",
      "sessions:write",
    ],
    editable: true,
  },
  {
    id: "billing",
    name: "Billing",
    description: "Manage billing and disputes",
    permissions: [
      "billing:read",
      "billing:write",
      "billing_adjustments:write",
      "disputes:read",
      "billing_disputes:write",
    ],
    editable: true,
  },
  {
    id: "viewer",
    name: "Viewer",
    description: "Read-only access to overview and reports",
    permissions: ["admin:read", "ops:read", "audit:read"],
    editable: true,
  },
];

export class MockAdminService implements AdminService {
  private kpis: KPIStat[];
  private opsMetrics: OpsMetric[];
  private jobs: OpsJob[];
  private alerts: OpsAlert[];
  private auditLogs: AuditLogEntry[];
  private approvals: ApprovalRequest[];
  private compliance: CompliancePolicyResult[];
  private users: AdminUser[];
  private apiKeys: ApiKeyRecord[];
  private sessions: SessionRecord[];
  private billingPlans: BillingPlan[];
  private billingAdjustments: BillingAdjustment[];
  private billingDisputes: BillingDispute[];
  private partners: PartnerRecord[];
  private connectors: ConnectorConfig[];
  private webhooks: WebhookDelivery[];
  private prompts: PromptRecord[];
  private budgets: LLMBudget[];
  private evaluations: EvaluationRun[];
  private residencyPolicies: ResidencyPolicy[];
  private retentionSchedules: RetentionSchedule[];
  private legalHolds: LegalHold[];
  private featureFlags: FeatureFlagRecord[];
  private releases: ReleaseRecord[];
  private settings: AdminSettings;
  private adminAudit: AdminAuditEvent[];
  private rulesets: RulesetRecord[];
  private rulesetAudit: RulesetAuditLog[];

  constructor() {
    const nowIso = now();

    this.kpis = [
      {
        id: "active-clients",
        label: "Active Clients",
        value: "128",
        change: 12,
        changeLabel: "+12% vs last month",
        changeDirection: "up",
        icon: Users,
        href: "partners-registry",
      },
      {
        id: "uptime",
        label: "Platform Uptime",
        value: "99.97%",
        change: 0.01,
        changeLabel: "+0.01%",
        changeDirection: "up",
        icon: Activity,
        href: "ops-monitoring",
      },
      {
        id: "alerts",
        label: "Open Alerts",
        value: "6",
        change: -3,
        changeLabel: "3 resolved this week",
        changeDirection: "down",
        icon: AlertTriangle,
        href: "ops-alerts",
      },
      {
        id: "approvals",
        label: "Pending Approvals",
        value: "9",
        change: 2,
        changeLabel: "+2 awaiting review",
        changeDirection: "up",
        icon: ShieldCheck,
        href: "audit-approvals",
      },
      {
        id: "revenue",
        label: "MRR",
        value: "$482K",
        change: 8,
        changeLabel: "+8% vs last month",
        changeDirection: "up",
        icon: DollarSign,
        href: "billing-plans",
      },
      {
        id: "slo",
        label: "SLO Compliance",
        value: "98.3%",
        change: -0.4,
        changeLabel: "Slightly below target",
        changeDirection: "down",
        icon: CheckCircle2,
        href: "ops-monitoring",
      },
    ];

    this.opsMetrics = [
      {
        id: "uptime",
        name: "Uptime",
        value: 99.97,
        unit: "%",
        change: 0.01,
        trend: "up",
        target: 99.95,
      },
      {
        id: "latency",
        name: "p95 Latency",
        value: 245,
        unit: "ms",
        change: -12,
        trend: "down",
        target: 300,
      },
      {
        id: "errors",
        name: "Error Rate",
        value: 0.12,
        unit: "%",
        change: -0.05,
        trend: "down",
        target: 0.5,
      },
      {
        id: "queue-depth",
        name: "Queue Depth",
        value: 34,
        change: 5,
        trend: "up",
        target: 50,
      },
    ];

    this.jobs = Array.from({ length: 32 }).map((_, index) => {
      const statusOrder: JobStatus[] = ["queued", "running", "succeeded", "failed", "scheduled"];
      const status = statusOrder[index % statusOrder.length];
      const createdAt = addMinutes(nowIso, -index * 30);
      const startedAt = status === "queued" ? undefined : addMinutes(createdAt, 1);
      const completedAt = ["succeeded", "failed"].includes(status)
        ? addMinutes(createdAt, 5 + index)
        : undefined;

      return {
        id: `job-${index + 1}`,
        name: ["Daily Settlement", "Fraud Sweep", "Email Digest", "Data Sync"][index % 4],
        type: ["cron", "workflow", "ingest"][index % 3],
        status,
        queue: ["critical", "standard", "bulk"][index % 3],
        retries: index % 3,
        maxRetries: 5,
        createdAt,
        startedAt,
        completedAt,
        nextRunAt: status === "scheduled" ? addMinutes(nowIso, (index % 16) * 15) : undefined,
        durationMs: completedAt && startedAt ? new Date(completedAt).getTime() - new Date(startedAt).getTime() : undefined,
        metadata: {
          shard: `cluster-${(index % 4) + 1}`,
        },
      } as OpsJob;
    });

    this.alerts = Array.from({ length: 15 }).map((_, index) => {
      const severity: OpsAlert["severity"][] = ["critical", "high", "medium", "low", "info"];
      const base = addMinutes(nowIso, -index * 20);
      const acknowledged = index % 3 === 0 ? addMinutes(base, 5) : undefined;
      const resolved = index % 5 === 0 ? addMinutes(base, 15) : undefined;
      return {
        id: `alert-${index + 1}`,
        title: [
          "Payment latency spike",
          "High error rate in ingestion",
          "New anomaly detected",
          "Partner API degradation",
        ][index % 4],
        severity: severity[index % severity.length],
        source: ["payments", "ingest", "llm", "partners"][index % 4],
        description: "Automated insight generated by platform monitoring.",
        createdAt: base,
        acknowledgedAt: acknowledged,
        resolvedAt: resolved,
        acknowledgedBy: acknowledged ? "ops.oncall@trdrhub.com" : undefined,
        tags: ["ops", "sla"].slice(0, (index % 2) + 1),
        link: "https://status.trdrhub.com/incidents/123",
      };
    });

    this.auditLogs = Array.from({ length: 120 }).map((_, index) => ({
      id: `audit-${index + 1}`,
      actor: {
        id: `user-${(index % 6) + 1}`,
        name: ["Alicia Chen", "Marcus Bell", "Samir Patel", "Luis Romero", "Evelyn Sparks", "Nina Alvarez"][index % 6],
        email: `admin${(index % 6) + 1}@trdrhub.com`,
        role: ROLES[index % ROLES.length].name,
      },
      action: ["created", "updated", "deleted", "invited", "revoked"][index % 5],
      entity: ["user", "apikey", "feature_flag", "partner", "plan"][index % 5],
      entityId: randomId(),
      summary: "Mock audit log entry describing an administrative action.",
      createdAt: addMinutes(nowIso, -index * 10),
      ip: `10.12.${index % 255}.${(index * 3) % 255}`,
      userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 13.2)",
      metadata: {
        change: "before/after snapshot omitted in mock",
      },
    }));

    this.approvals = Array.from({ length: 9 }).map((_, index) => {
      const status: ApprovalStatus[] = ["pending", "approved", "rejected"];
      const current = status[index % status.length];
      return {
        id: `approval-${index + 1}`,
        type: ["limit_increase", "policy_change", "sensitive_export"][index % 3],
        status: current,
        submittedBy: `ops+${index}@trdrhub.com`,
        submittedAt: addMinutes(nowIso, -index * 60),
        expiresAt: current === "pending" ? addMinutes(nowIso, 240) : undefined,
        approvers: ["Marcus Bell", "Samir Patel", "Evelyn Sparks"].slice(0, (index % 3) + 1),
        approvedAt: current === "approved" ? addMinutes(nowIso, -index * 45) : undefined,
        rejectedAt: current === "rejected" ? addMinutes(nowIso, -index * 30) : undefined,
        rejectionReason: current === "rejected" ? "Insufficient guardrail justification" : undefined,
        before: { limit: 1_000_000 },
        after: { limit: 2_500_000 },
        comments: [
          {
            id: randomId(),
            author: "Alicia Chen",
            body: "Please review the associated risk analysis before approving.",
            createdAt: addMinutes(nowIso, -index * 58),
          },
        ],
      } as ApprovalRequest;
    });

    this.compliance = [
      {
        id: "policy-1",
        name: "SOX Access Reviews",
        category: "Security",
        status: "pass",
        lastRunAt: addMinutes(nowIso, -360),
        exceptions: 0,
        owner: "compliance@trdrhub.com",
        reportUrl: "https://compliance.trdrhub.com/reports/sox",
      },
      {
        id: "policy-2",
        name: "Data Residency - EU",
        category: "Privacy",
        status: "warning",
        lastRunAt: addMinutes(nowIso, -120),
        exceptions: 3,
        owner: "privacy@trdrhub.com",
        reportUrl: "https://compliance.trdrhub.com/reports/gdpr",
      },
      {
        id: "policy-3",
        name: "AML Transaction Screening",
        category: "Financial",
        status: "fail",
        lastRunAt: addMinutes(nowIso, -90),
        exceptions: 5,
        owner: "aml@trdrhub.com",
      },
    ];

    this.users = Array.from({ length: 18 }).map((_, index) => {
      const role = ROLES[index % ROLES.length].id;
      const status: AdminUser["status"][] = ["active", "invited", "disabled"];
      return {
        id: `admin-${index + 1}`,
        name: ["Alicia Chen", "Marcus Bell", "Samir Patel", "Luis Romero", "Evelyn Sparks", "Nina Alvarez"][index % 6],
        email: `admin${index + 1}@trdrhub.com`,
        role,
        status: status[index % status.length],
        invitedAt: addMinutes(nowIso, -index * 120),
        lastActiveAt: status[index % status.length] === "active" ? addMinutes(nowIso, -index * 45) : undefined,
        mfaEnabled: index % 2 === 0,
        tenants: ["global", "emea", "apac"].slice(0, (index % 3) + 1),
      } as AdminUser;
    });

    this.apiKeys = Array.from({ length: 6 }).map((_, index) => ({
      id: `key-${index + 1}`,
      name: ["Production API", "Webhook Signer", "Partner Sandbox"][index % 3],
      status: ["active", "rotating", "revoked", "expired"][index % 4] as ApiKeyRecord["status"],
      createdAt: addMinutes(nowIso, -index * 300),
      lastUsedAt: addMinutes(nowIso, -index * 30),
      expiresAt: index % 4 === 3 ? addMinutes(nowIso, -30) : addMinutes(nowIso, 90 * 24 * 60),
      scopes: ["ingest", "read", "write"].slice(0, (index % 3) + 1),
      environment: ["production", "staging", "development"][index % 3] as ApiKeyRecord["environment"],
      hashedKey: `hash-${randomId()}`,
    }));

    this.sessions = Array.from({ length: 20 }).map((_, index) => ({
      id: `session-${index + 1}`,
      userId: this.users[index % this.users.length].id,
      createdAt: addMinutes(nowIso, -index * 240),
      lastSeenAt: addMinutes(nowIso, -index * 35),
      ipAddress: `172.16.${index % 255}.${(index * 7) % 255}`,
      location: ["New York, USA", "London, UK", "Singapore", "Sydney, AU"][index % 4],
      userAgent: "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.0) AppleWebKit/605.1.15",
      device: ["MacBook Pro", "Windows Desktop", "iPad", "Pixel 7"][index % 4],
      platform: ["macOS", "windows", "ios", "android"][index % 4],
      riskLevel: ["low", "medium", "high"][index % 3] as SessionRecord["riskLevel"],
    }));

    this.billingPlans = [
      {
        id: "plan-free",
        name: "Starter",
        tier: "free",
        pricePerMonth: 0,
        currency: "USD",
        features: ["Up to 100 LCs", "Community support", "Basic analytics"],
        limits: { teams: 1, members: 5 },
        status: "active",
      },
      {
        id: "plan-growth",
        name: "Growth",
        tier: "growth",
        pricePerMonth: 1999,
        currency: "USD",
        features: ["5,000 LCs", "Priority support", "Advanced analytics", "LLM risk checks"],
        limits: { teams: 5, members: 50 },
        status: "active",
      },
      {
        id: "plan-enterprise",
        name: "Enterprise",
        tier: "enterprise",
        pricePerMonth: 4999,
        currency: "USD",
        features: ["Unlimited LCs", "Dedicated CSM", "On-prem connectors", "Custom SLAs"],
        limits: { teams: "unlimited", members: "unlimited" },
        status: "active",
      },
    ];

    this.billingAdjustments = Array.from({ length: 12 }).map((_, index) => ({
      id: `adjustment-${index + 1}`,
      customer: ["Bank of Asia", "GlobalTrade Inc.", "LatAm Exports"][index % 3],
      amount: index % 2 === 0 ? 25000 : -15000,
      currency: "USD",
      reason: index % 2 === 0 ? "Usage overage" : "Service credit",
      createdAt: addMinutes(nowIso, -index * 1440),
      createdBy: "billing@trdrhub.com",
      status: ["pending", "posted", "void"][index % 3] as BillingAdjustment["status"],
    }));

    this.billingDisputes = Array.from({ length: 6 }).map((_, index) => ({
      id: `dispute-${index + 1}`,
      customer: ["Regency Trade", "Pacific Credit", "Global Freight"][index % 3],
      amount: 42000 + index * 3000,
      currency: "USD",
      reason: ["Duplicate charge", "Service not rendered", "Contract mismatch"][index % 3],
      openedAt: addMinutes(nowIso, -index * 720),
      status: ["open", "won", "lost", "under_review"][index % 4] as BillingDispute["status"],
      evidenceDueAt: addMinutes(nowIso, 3 * 24 * 60),
      notes: "Awaiting additional documentation from customer",
    }));

    this.partners = [
      {
        id: "partner-1",
        name: "FinStack",
        category: "Risk Data",
        status: "active",
        contactEmail: "partnerships@finstack.com",
        createdAt: addMinutes(nowIso, -10_000),
        updatedAt: addMinutes(nowIso, -1_000),
        markets: ["US", "UK", "SG"],
      },
      {
        id: "partner-2",
        name: "TradeBridge",
        category: "Compliance",
        status: "inactive",
        contactEmail: "ops@tradebridge.io",
        createdAt: addMinutes(nowIso, -15_000),
        updatedAt: addMinutes(nowIso, -2_000),
        markets: ["EU", "MENA"],
      },
    ];

    this.connectors = [
      {
        id: "connector-1",
        name: "SAP S/4HANA",
        provider: "SAP",
        status: "enabled",
        lastSyncAt: addMinutes(nowIso, -30),
        authType: "oauth",
        hasSecrets: true,
        config: {
          region: "eu-central-1",
          clientId: "sap-oauth-client",
        },
      },
      {
        id: "connector-2",
        name: "Oracle EBS",
        provider: "Oracle",
        status: "disabled",
        lastSyncAt: addMinutes(nowIso, -1440),
        authType: "api_key",
        hasSecrets: true,
        config: {
          endpoint: "https://oracle.example.com",
        },
      },
    ];

    this.webhooks = Array.from({ length: 25 }).map((_, index) => ({
      id: `wh-${index + 1}`,
      endpoint: "https://hooks.partner.com/lc-events",
      status: ["delivered", "pending", "failed"][index % 3] as WebhookDelivery["status"],
      event: ["lc.validated", "lc.discrepancy", "lc.uploaded"][index % 3],
      sentAt: addMinutes(nowIso, -index * 5),
      responseCode: [200, 200, 500][index % 3],
      retryCount: index % 2,
      lastError: index % 3 === 2 ? "Timeout" : undefined,
    }));

    const promptBase: PromptVersion = {
      id: randomId(),
      version: 3,
      createdAt: addMinutes(nowIso, -120),
      createdBy: "prompt.team@trdrhub.com",
      diffSummary: "Improved entity extraction for import LC",
      prompt: "You are LC CoPilot. Extract structured data from documents...",
      variables: ["client_name", "document_type"],
    };

    this.prompts = [
      {
        id: "prompt-import",
        name: "Import LC Validation",
        description: "Ensures import LC documents meet compliance standards",
        useCase: "import",
        latestVersion: promptBase,
        versions: [
          { ...promptBase, version: 1, createdAt: addMinutes(nowIso, -720) },
          { ...promptBase, version: 2, createdAt: addMinutes(nowIso, -360) },
          promptBase,
        ],
        status: "active",
      },
    ];

    this.budgets = [
      {
        id: "budget-1",
        service: "LC CoPilot",
        provider: "OpenAI",
        monthlyLimit: 2500,
        currency: "USD",
        spendingToDate: 1420,
        forecast: 2100,
        hardLimit: 3500,
        emails: ["llm-finance@trdrhub.com"],
      },
      {
        id: "budget-2",
        service: "Trade Risk Evaluator",
        provider: "Anthropic",
        monthlyLimit: 1500,
        currency: "USD",
        spendingToDate: 890,
        forecast: 1300,
        hardLimit: 2000,
        emails: ["llm-team@trdrhub.com", "risk@trdrhub.com"],
      },
    ];

    this.evaluations = Array.from({ length: 14 }).map((_, index) => ({
      id: `eval-${index + 1}`,
      name: `LC risk scoring eval ${index + 1}`,
      model: ["gpt-4.1", "claude-3-opus", "mixtral-8x7b"][index % 3],
      dataset: ["sanctioned-lcs", "high-risk-imports", "standard-trade"][index % 3],
      status: ["pending", "running", "completed", "failed"][index % 4] as EvaluationRun["status"],
      startedAt: addMinutes(nowIso, -index * 180),
      completedAt: index % 4 === 2 ? addMinutes(nowIso, -index * 120) : undefined,
      metrics: {
        accuracy: Number((0.65 + (index % 5) * 0.05).toFixed(2)),
        latencyMs: 1800 - index * 20,
        cost: Number((35 + index * 1.5).toFixed(2)),
        score: Number((0.7 + (index % 3) * 0.08).toFixed(2)),
      },
      regressions: index % 4 === 3 ? ["False positive rate increased"] : undefined,
    }));

    this.residencyPolicies = [
      {
        id: "residency-eu",
        region: "EU",
        storageLocation: "Frankfurt, DE",
        status: "compliant",
        lastValidatedAt: addMinutes(nowIso, -240),
        owner: "privacy@trdrhub.com",
      },
      {
        id: "residency-gcc",
        region: "GCC",
        storageLocation: "Dubai, UAE",
        status: "waived",
        lastValidatedAt: addMinutes(nowIso, -720),
        owner: "privacy@trdrhub.com",
        notes: "Waiver approved until 2025-12-31",
      },
      {
        id: "residency-india",
        region: "India",
        storageLocation: "Mumbai, IN",
        status: "non_compliant",
        lastValidatedAt: addMinutes(nowIso, -90),
        owner: "privacy@trdrhub.com",
        notes: "Awaiting DC expansion",
      },
    ];

    this.retentionSchedules = [
      {
        id: "retention-std",
        name: "Standard LC Records",
        policy: "Retain for 7 years",
        appliesTo: ["lc_uploads", "analysis_results"],
        retentionDays: 2555,
        lastRunAt: addMinutes(nowIso, -1440),
        nextRunAt: addMinutes(nowIso, 24 * 60),
        dryRunSummary: "172 records eligible for deletion",
      },
      {
        id: "retention-logs",
        name: "Security Logs",
        policy: "Retain for 365 days",
        appliesTo: ["auth_logs", "admin_activity"],
        retentionDays: 365,
        lastRunAt: addMinutes(nowIso, -60),
        nextRunAt: addMinutes(nowIso, 6 * 60),
      },
    ];

    this.legalHolds = [
      {
        id: "hold-1",
        name: "Regulatory Review Q3",
        status: "active",
        createdAt: addMinutes(nowIso, -10 * 24 * 60),
        owner: "legal@trdrhub.com",
        affectedObjects: 248,
        notes: "Covering all transactions with counterpart A.",
      },
      {
        id: "hold-2",
        name: "Litigation Contingency",
        status: "released",
        createdAt: addMinutes(nowIso, -120 * 24 * 60),
        releasedAt: addMinutes(nowIso, -14 * 24 * 60),
        owner: "legal@trdrhub.com",
        affectedObjects: 120,
        notes: "Released after settlement.",
      },
    ];

    this.featureFlags = [
      {
        id: "flag-new-analytics",
        name: "New Analytics Dashboard",
        description: "Rollout of analytics v2",
        status: "enabled",
        createdAt: addMinutes(nowIso, -5 * 24 * 60),
        updatedAt: addMinutes(nowIso, -24 * 60),
        owner: "product@trdrhub.com",
        targeting: {
          environments: ["production", "staging"],
          percentageRollout: 75,
        },
        tags: ["analytics", "dashboard"],
      },
      {
        id: "flag-llm-guardrails",
        name: "LLM Guardrails",
        description: "Enable new guardrail checks",
        status: "scheduled",
        createdAt: addMinutes(nowIso, -3 * 24 * 60),
        updatedAt: addMinutes(nowIso, -3 * 24 * 60),
        owner: "llm@trdrhub.com",
        targeting: {
          environments: ["staging"],
          tenants: ["beta"],
        },
        tags: ["llm", "risk"],
      },
    ];

    this.releases = Array.from({ length: 18 }).map((_, index) => ({
      id: `rel-${index + 1}`,
      version: `v2.${24 - index}.0`,
      deployedAt: addMinutes(nowIso, -index * 180),
      environment: ["production", "staging", "sandbox"][index % 3],
      author: ["CI/CD", "Sarah Jenkins", "DevOps Bot"][index % 3],
      summary: "Deployment summary placeholder for mock data.",
      commitSha: `abc${index}123`,
      pullRequestUrl: "https://github.com/ripclass/trdrhub.com/pull/123",
      status: ["succeeded", "failed", "in_progress"][index % 3] as ReleaseRecord["status"],
      services: [
        { name: "web", previousVersion: `v2.${23 - index}.0` },
        { name: "api", previousVersion: `v2.${23 - index}.0` },
      ],
    }));

    this.settings = {
      branding: {
        primaryColor: "#1d4ed8",
        logoUrl: "https://trdrhub.com/assets/logo.svg",
        supportEmail: "support@trdrhub.com",
      },
      authentication: {
        passwordPolicy: "min 12 chars, 1 special, 1 number",
        mfaEnforced: true,
        ssoEnabled: true,
        sessionTimeoutMinutes: 60,
      },
      notifications: {
        dailySummary: true,
        weeklyInsights: true,
        criticalAlerts: true,
        digestEmail: "executive@trdrhub.com",
      },
    };

    this.adminAudit = [];

    // Initialize rulesets mock data
    this.rulesets = [
      {
        id: "ruleset-1",
        domain: "icc",
        jurisdiction: "global",
        rulesetVersion: "1.0.0",
        rulebookVersion: "UCP600:2007",
        filePath: "rules/icc/icc-ucp600-v1.0.0.json",
        status: "active",
        checksumMd5: "a3f1c28f9e24bcd0a2b7318c4d7b56d2",
        ruleCount: 39,
        createdAt: addMinutes(nowIso, -30 * 24 * 60),
        publishedAt: addMinutes(nowIso, -30 * 24 * 60),
        publishedBy: "admin-1",
      },
      {
        id: "ruleset-2",
        domain: "icc",
        jurisdiction: "global",
        rulesetVersion: "1.1.0",
        rulebookVersion: "UCP600:2007",
        filePath: "rules/icc/icc-ucp600-v1.1.0.json",
        status: "draft",
        checksumMd5: "b4e2d39g0f35cde1b3c842d5e8c67e3f",
        ruleCount: 42,
        createdAt: addMinutes(nowIso, -5 * 24 * 60),
        createdBy: "admin-1",
        notes: "Updated with additional validation rules",
      },
      {
        id: "ruleset-3",
        domain: "regulations",
        jurisdiction: "eu",
        rulesetVersion: "1.0.0",
        rulebookVersion: "EU-Trade:2024",
        filePath: "rules/regulations/eu-v1.0.0.json",
        status: "active",
        checksumMd5: "c5f3e4a0h46def2c4d953e6f9d78f4g",
        ruleCount: 15,
        createdAt: addMinutes(nowIso, -20 * 24 * 60),
        publishedAt: addMinutes(nowIso, -20 * 24 * 60),
        publishedBy: "admin-1",
      },
      {
        id: "ruleset-4",
        domain: "regulations",
        jurisdiction: "us",
        rulesetVersion: "1.0.0",
        rulebookVersion: "US-Customs:2024",
        filePath: "rules/regulations/us-v1.0.0.json",
        status: "active",
        checksumMd5: "d6g4f5b1i57efg3d5ea64g7a0e89g5h",
        ruleCount: 12,
        createdAt: addMinutes(nowIso, -15 * 24 * 60),
        publishedAt: addMinutes(nowIso, -15 * 24 * 60),
        publishedBy: "admin-1",
      },
      {
        id: "ruleset-5",
        domain: "regulations",
        jurisdiction: "bd",
        rulesetVersion: "1.0.0",
        rulebookVersion: "BD-Central-Bank:2024",
        filePath: "rules/regulations/bd-v1.0.0.json",
        status: "active",
        checksumMd5: "e7h5g6c2j68fgh4e6fb75h8b1f90h6i",
        ruleCount: 18,
        createdAt: addMinutes(nowIso, -10 * 24 * 60),
        publishedAt: addMinutes(nowIso, -10 * 24 * 60),
        publishedBy: "admin-1",
      },
    ];

    this.rulesetAudit = [
      {
        id: "audit-1",
        rulesetId: "ruleset-1",
        action: "upload",
        actorId: "admin-1",
        createdAt: addMinutes(nowIso, -30 * 24 * 60),
        detail: { ruleCount: 39 },
      },
      {
        id: "audit-2",
        rulesetId: "ruleset-1",
        action: "validate",
        actorId: "admin-1",
        createdAt: addMinutes(nowIso, -30 * 24 * 60),
        detail: { valid: true },
      },
      {
        id: "audit-3",
        rulesetId: "ruleset-1",
        action: "publish",
        actorId: "admin-1",
        createdAt: addMinutes(nowIso, -30 * 24 * 60),
      },
    ];
  }

  private paginate<T>(collection: T[], params: Partial<PaginateParams>): PaginatedResult<T> {
    const { page, pageSize } = { ...PAGE_DEFAULT, ...params };
    const start = (page - 1) * pageSize;
    const items = collection.slice(start, start + pageSize);
    return {
      items,
      page,
      pageSize,
      total: collection.length,
    };
  }

  async getDashboardStats(range: TimeRange): Promise<KPIStat[]> {
    void range;
    return clone(this.kpis);
  }

  async getOpsMetrics(range: TimeRange): Promise<OpsMetric[]> {
    void range;
    return clone(this.opsMetrics);
  }

  async listJobs(params: { page: number; pageSize: number; status?: JobStatus[]; search?: string }): Promise<PaginatedResult<OpsJob>> {
    try {
      const { status, search } = params;
      let results = [...this.jobs];
      if (status?.length) {
        results = results.filter((job) => status.includes(job.status));
      }
      if (search) {
        const term = search.toLowerCase();
        results = results.filter((job) => job.name.toLowerCase().includes(term) || job.id.includes(term));
      }
      return this.paginate(results, params);
    } catch (error) {
      console.error("MockAdminService.listJobs failed, returning fallback data", error);
      return this.paginate([...this.jobs], params);
    }
  }

  async retryJob(id: string): Promise<MutationResult> {
    const job = this.jobs.find((item) => item.id === id);
    if (!job) return { success: false, message: "Job not found" };
    job.status = "queued";
    job.retries = Math.max(0, job.retries - 1);
    job.startedAt = undefined;
    job.completedAt = undefined;
    job.metadata = { ...job.metadata, retriedAt: now() };
    return { success: true, message: "Job re-queued" };
  }

  async cancelJob(id: string): Promise<MutationResult> {
    const job = this.jobs.find((item) => item.id === id);
    if (!job) return { success: false, message: "Job not found" };
    job.status = "cancelled";
    job.completedAt = now();
    return { success: true, message: "Job cancelled" };
  }

  async listAlerts(params: { page: number; pageSize: number; severity?: OpsAlert["severity"][]; status?: "active" | "acknowledged" | "resolved" }): Promise<PaginatedResult<OpsAlert>> {
    try {
      const { severity, status } = params;
      let results = [...this.alerts];
      if (severity?.length) {
        results = results.filter((alert) => severity.includes(alert.severity));
      }
      if (status) {
        results = results.filter((alert) => {
          if (status === "active") return !alert.acknowledgedAt;
          if (status === "acknowledged") return !!alert.acknowledgedAt && !alert.resolvedAt;
          if (status === "resolved") return !!alert.resolvedAt;
          return true;
        });
      }
      return this.paginate(results, params);
    } catch (error) {
      console.error("MockAdminService.listAlerts failed, returning fallback data", error);
      return this.paginate([...this.alerts], params);
    }
  }

  async acknowledgeAlert(id: string): Promise<MutationResult> {
    const alert = this.alerts.find((item) => item.id === id);
    if (!alert) return { success: false, message: "Alert not found" };
    alert.acknowledgedAt = now();
    alert.acknowledgedBy = "operations@trdrhub.com";
    return { success: true, message: "Alert acknowledged" };
  }

  async snoozeAlert(id: string, minutes: number): Promise<MutationResult> {
    const alert = this.alerts.find((item) => item.id === id);
    if (!alert) return { success: false, message: "Alert not found" };
    // Note: OpsAlert doesn't have a metadata field, so we just mark it as acknowledged
    // In a real implementation, you might want to add a snoozedUntil field to OpsAlert
    return { success: true, message: `Alert snoozed for ${minutes} minutes` };
  }

  async listAuditLogs(params: { page: number; pageSize: number; search?: string; actor?: string; action?: string }): Promise<PaginatedResult<AuditLogEntry>> {
    let results = [...this.auditLogs];
    if (params.search) {
      const term = params.search.toLowerCase();
      results = results.filter((log) =>
        log.summary.toLowerCase().includes(term) ||
        log.actor.name.toLowerCase().includes(term) ||
        log.entity.toLowerCase().includes(term),
      );
    }
    if (params.actor) {
      results = results.filter((log) => log.actor.email === params.actor || log.actor.name === params.actor);
    }
    if (params.action) {
      results = results.filter((log) => log.action === params.action);
    }
    return this.paginate(results, params);
  }

  async listApprovalRequests(params: { status: ApprovalStatus; page: number; pageSize: number }): Promise<PaginatedResult<ApprovalRequest>> {
    const results = this.approvals.filter((approval) => approval.status === params.status);
    return this.paginate(results, params);
  }

  async resolveApproval(id: string, outcome: "approve" | "reject", reason?: string): Promise<MutationResult> {
    const approval = this.approvals.find((item) => item.id === id);
    if (!approval) return { success: false, message: "Approval not found" };
    approval.status = outcome === "approve" ? "approved" : "rejected";
    approval.approvedAt = outcome === "approve" ? now() : undefined;
    approval.rejectedAt = outcome === "reject" ? now() : undefined;
    approval.rejectionReason = reason;
    return { success: true, message: `Request ${outcome}d` };
  }

  async getComplianceSummary(): Promise<CompliancePolicyResult[]> {
    return clone(this.compliance);
  }

  async listUsers(params: { page: number; pageSize: number; search?: string; role?: AdminRole | "all" }): Promise<PaginatedResult<AdminUser>> {
    let results = [...this.users];
    if (params.role && params.role !== "all") {
      results = results.filter((user) => user.role === params.role);
    }
    if (params.search) {
      const term = params.search.toLowerCase();
      results = results.filter((user) =>
        user.name.toLowerCase().includes(term) || user.email.toLowerCase().includes(term),
      );
    }
    return this.paginate(results, params);
  }

  async inviteUser(payload: { email: string; role: AdminRole }): Promise<MutationResult> {
    const exists = this.users.some((user) => user.email === payload.email);
    if (exists) return { success: false, message: "User already invited" };
    const newUser: AdminUser = {
      id: `admin-${this.users.length + 1}`,
      name: payload.email.split("@")[0],
      email: payload.email,
      role: payload.role,
      status: "invited",
      invitedAt: now(),
      mfaEnabled: false,
      tenants: ["global"],
    };
    this.users.unshift(newUser);
    return { success: true, message: "Invite sent" };
  }

  async disableUser(id: string): Promise<MutationResult> {
    const user = this.users.find((item) => item.id === id);
    if (!user) return { success: false, message: "User not found" };
    user.status = "disabled";
    return { success: true, message: "User disabled" };
  }

  async updateUserRole(id: string, role: AdminRole): Promise<MutationResult<AdminUser>> {
    const user = this.users.find((item) => item.id === id);
    if (!user) return { success: false, message: "User not found" };
    user.role = role;
    return { success: true, data: clone(user) };
  }

  async listRoles(): Promise<RoleDefinition[]> {
    return clone(ROLES);
  }

  async listApiKeys(params: { page: number; pageSize: number; environment?: string }): Promise<PaginatedResult<ApiKeyRecord>> {
    let results = [...this.apiKeys];
    if (params.environment) {
      results = results.filter((key) => key.environment === params.environment);
    }
    return this.paginate(results, params);
  }

  async createApiKey(payload: { name: string; scopes: string[]; environment: string }): Promise<MutationResult<{ token: string }>> {
    const token = `trdr_${randomId()}${randomId()}`;
    const record: ApiKeyRecord = {
      id: `key-${this.apiKeys.length + 1}`,
      name: payload.name,
      status: "active",
      createdAt: now(),
      scopes: payload.scopes,
      environment: payload.environment as ApiKeyRecord["environment"],
      hashedKey: `hash-${randomId()}`,
    };
    this.apiKeys.unshift(record);
    return { success: true, data: { token }, message: "API key created" };
  }

  async rotateApiKey(id: string): Promise<MutationResult<{ token: string }>> {
    const key = this.apiKeys.find((item) => item.id === id);
    if (!key) return { success: false, message: "API key not found" };
    const token = `trdr_${randomId()}${randomId()}`;
    key.status = "rotating";
    key.hashedKey = `hash-${randomId()}`;
    key.lastUsedAt = now();
    return { success: true, data: { token }, message: "Rotation started" };
  }

  async revokeApiKey(id: string): Promise<MutationResult> {
    const key = this.apiKeys.find((item) => item.id === id);
    if (!key) return { success: false, message: "API key not found" };
    key.status = "revoked";
    key.expiresAt = now();
    return { success: true, message: "API key revoked" };
  }

  async listSessions(params: { page: number; pageSize: number; risk?: SessionRecord["riskLevel"] }): Promise<PaginatedResult<SessionRecord>> {
    let results = [...this.sessions];
    if (params.risk) {
      results = results.filter((session) => session.riskLevel === params.risk);
    }
    return this.paginate(results, params);
  }

  async revokeSession(id: string): Promise<MutationResult> {
    const session = this.sessions.find((item) => item.id === id);
    if (!session) return { success: false, message: "Session not found" };
    this.sessions = this.sessions.filter((item) => item.id !== id);
    return { success: true, message: "Session revoked" };
  }

  async getBillingSummary(range?: TimeRange, currency?: string): Promise<BillingSummary> {
    // Try to get from aggregator first, fallback to mock
    try {
      const { getBillingSummaryFromAggregator } = await import("../billingIntegration");
      const aggregatorResult = await getBillingSummaryFromAggregator(range, currency);
      
      if (aggregatorResult) {
        return aggregatorResult;
      }
    } catch (error) {
      console.warn("Billing aggregator not available, using mock", error);
    }

    // Fallback to mock calculation
    void range; // Ignore range for now in mock
    void currency; // Ignore currency for now in mock

    // Compute MRR from active plans (sum of pricePerMonth in cents)
    const mrrCents = this.billingPlans
      .filter((plan) => plan.status === "active")
      .reduce((sum, plan) => sum + plan.pricePerMonth, 0);

    // ARR = MRR * 12
    const arrCents = mrrCents * 12;

    // Month-to-date revenue: sum of posted adjustments + synthetic payments
    // For mock, use posted adjustments and add some synthetic payment data
    const monthStart = new Date();
    monthStart.setDate(1);
    monthStart.setHours(0, 0, 0, 0);

    const postedAdjustments = this.billingAdjustments
      .filter((adj) => adj.status === "posted" && new Date(adj.createdAt) >= monthStart)
      .reduce((sum, adj) => sum + Math.max(0, adj.amount), 0);

    // Synthetic payments for mock (simulate some monthly recurring revenue)
    const syntheticPayments = mrrCents * 0.85; // Assume 85% collection rate for mock

    const monthToDateCents = postedAdjustments + syntheticPayments;

    // Refunds: sum of negative adjustments
    const refundsCents = Math.abs(
      this.billingAdjustments
        .filter((adj) => adj.status === "posted" && new Date(adj.createdAt) >= monthStart && adj.amount < 0)
        .reduce((sum, adj) => sum + adj.amount, 0)
    );

    // Net revenue = MTD - refunds
    const netRevenueCents = monthToDateCents - refundsCents;

    // Disputes open: count disputes with status "open" or "under_review"
    const disputesOpen = this.billingDisputes.filter(
      (dispute) => dispute.status === "open" || dispute.status === "under_review"
    ).length;

    // Invoices this month: synthetic count (would come from invoice service)
    const invoicesThisMonth = Math.floor(mrrCents / 2000); // Rough estimate

    // Adjustments pending: count adjustments with status "pending"
    const adjustmentsPending = this.billingAdjustments.filter((adj) => adj.status === "pending").length;

    return {
      mrrCents,
      arrCents,
      monthToDateCents: Math.round(monthToDateCents),
      netRevenueCents: Math.round(netRevenueCents),
      refundsCents: Math.round(refundsCents),
      disputesOpen,
      invoicesThisMonth,
      adjustmentsPending,
    };
  }

  async listBillingPlans(): Promise<BillingPlan[]> {
    return clone(this.billingPlans);
  }

  async updateBillingPlan(id: string, payload: Partial<BillingPlan>): Promise<MutationResult<BillingPlan>> {
    const planIndex = this.billingPlans.findIndex((plan) => plan.id === id);
    if (planIndex === -1) {
      return { success: false, message: "Plan not found" };
    }

    const updated: BillingPlan = {
      ...this.billingPlans[planIndex],
      ...payload,
      features: payload.features ?? this.billingPlans[planIndex].features,
      limits: payload.limits ?? this.billingPlans[planIndex].limits,
    };

    this.billingPlans[planIndex] = updated;
    return { success: true, data: clone(updated), message: "Plan updated" };
  }

  async listBillingAdjustments(params: { page: number; pageSize: number }): Promise<PaginatedResult<BillingAdjustment>> {
    return this.paginate(this.billingAdjustments, params);
  }

  async addBillingAdjustment(payload: BillingAdjustment): Promise<MutationResult> {
    this.billingAdjustments.unshift({ ...payload, id: `adjustment-${this.billingAdjustments.length + 1}` });
    return { success: true, message: "Adjustment recorded" };
  }

  async listBillingDisputes(params: { page: number; pageSize: number; status?: BillingDispute["status"][] }): Promise<PaginatedResult<BillingDispute>> {
    let results = [...this.billingDisputes];
    if (params.status?.length) {
      results = results.filter((dispute) => params.status?.includes(dispute.status));
    }
    return this.paginate(results, params);
  }

  async resolveDispute(id: string, outcome: "won" | "lost" | "write_off", notes?: string): Promise<MutationResult> {
    const dispute = this.billingDisputes.find((item) => item.id === id);
    if (!dispute) return { success: false, message: "Dispute not found" };
    dispute.status = outcome === "write_off" ? "lost" : outcome;
    dispute.notes = notes;
    return { success: true, message: `Dispute marked ${outcome}` };
  }

  async listPartners(): Promise<PartnerRecord[]> {
    return clone(this.partners);
  }

  async setPartnerStatus(id: string, status: PartnerRecord["status"]): Promise<MutationResult> {
    const partner = this.partners.find((item) => item.id === id);
    if (!partner) return { success: false, message: "Partner not found" };
    partner.status = status;
    partner.updatedAt = now();
    return { success: true, message: "Partner status updated" };
  }

  async listConnectors(): Promise<ConnectorConfig[]> {
    return clone(this.connectors);
  }

  async updateConnector(id: string, config: Partial<ConnectorConfig>): Promise<MutationResult> {
    const connector = this.connectors.find((item) => item.id === id);
    if (!connector) return { success: false, message: "Connector not found" };
    this.connectors = this.connectors.map((item) => (item.id === id ? { ...item, ...config, config: { ...item.config, ...config.config } } : item));
    return { success: true, message: "Connector updated" };
  }

  async listWebhookDeliveries(params: { page: number; pageSize: number; status?: WebhookDelivery["status"] }): Promise<PaginatedResult<WebhookDelivery>> {
    let results = [...this.webhooks];
    if (params.status) {
      results = results.filter((delivery) => delivery.status === params.status);
    }
    return this.paginate(results, params);
  }

  async redeliverWebhook(id: string): Promise<MutationResult> {
    const delivery = this.webhooks.find((item) => item.id === id);
    if (!delivery) return { success: false, message: "Delivery not found" };
    delivery.status = "pending";
    delivery.retryCount += 1;
    delivery.lastError = undefined;
    return { success: true, message: "Redelivery triggered" };
  }

  async rotateWebhookSecret(id: string): Promise<MutationResult<{ secret: string }>> {
    const connector = this.connectors.find((item) => item.id === id);
    if (!connector) return { success: false, message: "Webhook not found" };
    const secret = `whsec_${randomId()}${randomId()}`;
    connector.config = { ...connector.config, signingSecret: secret };
    return { success: true, data: { secret }, message: "Secret rotated" };
  }

  async listPrompts(): Promise<PromptRecord[]> {
    return clone(this.prompts);
  }

  async publishPromptVersion(id: string, payload: Partial<PromptVersion>): Promise<MutationResult<PromptRecord>> {
    const prompt = this.prompts.find((item) => item.id === id);
    if (!prompt) return { success: false, message: "Prompt not found" };
    const version: PromptVersion = {
      id: randomId(),
      version: prompt.latestVersion.version + 1,
      createdAt: now(),
      createdBy: payload.createdBy ?? "prompt.team@trdrhub.com",
      diffSummary: payload.diffSummary ?? "Minor improvements",
      prompt: payload.prompt ?? prompt.latestVersion.prompt,
      variables: payload.variables ?? prompt.latestVersion.variables,
    };
    prompt.versions.unshift(version);
    prompt.latestVersion = version;
    return { success: true, data: clone(prompt), message: "Prompt published" };
  }

  async listLLMBudgets(): Promise<LLMBudget[]> {
    return clone(this.budgets);
  }

  async updateLLMBudget(id: string, payload: Partial<LLMBudget>): Promise<MutationResult> {
    const budget = this.budgets.find((item) => item.id === id);
    if (!budget) return { success: false, message: "Budget not found" };
    Object.assign(budget, payload);
    return { success: true, message: "Budget updated" };
  }

  async listEvaluationRuns(params: { page: number; pageSize: number; status?: EvaluationRun["status"][] }): Promise<PaginatedResult<EvaluationRun>> {
    let results = [...this.evaluations];
    if (params.status?.length) {
      results = results.filter((run) => params.status?.includes(run.status));
    }
    return this.paginate(results, params);
  }

  async listResidencyPolicies(): Promise<ResidencyPolicy[]> {
    return clone(this.residencyPolicies);
  }

  async listRetentionSchedules(): Promise<RetentionSchedule[]> {
    return clone(this.retentionSchedules);
  }

  async runRetentionSchedule(id: string, dryRun = false): Promise<MutationResult<{ summary?: string }>> {
    const schedule = this.retentionSchedules.find((item) => item.id === id);
    if (!schedule) return { success: false, message: "Schedule not found" };
    schedule.lastRunAt = now();
    schedule.dryRunSummary = dryRun ? "Dry run: 84 records would be removed." : undefined;
    return { success: true, data: { summary: schedule.dryRunSummary } };
  }

  async listLegalHolds(): Promise<LegalHold[]> {
    return clone(this.legalHolds);
  }

  async createLegalHold(payload: Partial<LegalHold>): Promise<MutationResult<LegalHold>> {
    const hold: LegalHold = {
      id: `hold-${this.legalHolds.length + 1}`,
      name: payload.name ?? "New Legal Hold",
      status: "active",
      createdAt: now(),
      owner: payload.owner ?? "legal@trdrhub.com",
      affectedObjects: payload.affectedObjects ?? 0,
      notes: payload.notes,
    };
    this.legalHolds.unshift(hold);
    return { success: true, data: clone(hold) };
  }

  async releaseLegalHold(id: string): Promise<MutationResult> {
    const hold = this.legalHolds.find((item) => item.id === id);
    if (!hold) return { success: false, message: "Legal hold not found" };
    hold.status = "released";
    hold.releasedAt = now();
    return { success: true, message: "Legal hold released" };
  }

  async listFeatureFlags(): Promise<FeatureFlagRecord[]> {
    return clone(this.featureFlags);
  }

  async setFeatureFlagStatus(id: string, status: FeatureFlagRecord["status"]): Promise<MutationResult> {
    const flag = this.featureFlags.find((item) => item.id === id);
    if (!flag) return { success: false, message: "Feature flag not found" };
    flag.status = status;
    flag.updatedAt = now();
    return { success: true, message: "Flag updated" };
  }

  async updateFeatureFlagTargeting(id: string, targeting: FeatureFlagTargeting): Promise<MutationResult> {
    const flag = this.featureFlags.find((item) => item.id === id);
    if (!flag) return { success: false, message: "Feature flag not found" };
    flag.targeting = targeting;
    flag.updatedAt = now();
    return { success: true, message: "Targeting updated" };
  }

  async listReleases(params: { page: number; pageSize: number; environment?: string }): Promise<PaginatedResult<ReleaseRecord>> {
    let results = [...this.releases];
    if (params.environment) {
      results = results.filter((release) => release.environment === params.environment);
    }
    return this.paginate(results, params);
  }

  async getSettings(): Promise<AdminSettings> {
    return clone(this.settings);
  }

  async updateSettings(settings: Partial<AdminSettings>): Promise<MutationResult<AdminSettings>> {
    this.settings = {
      branding: { ...this.settings.branding, ...settings.branding },
      authentication: { ...this.settings.authentication, ...settings.authentication },
      notifications: { ...this.settings.notifications, ...settings.notifications },
    };
    return { success: true, data: clone(this.settings), message: "Settings saved" };
  }

  async listRulesets(params: { page: number; pageSize: number; domain?: string; jurisdiction?: string; status?: RulesetStatus }): Promise<PaginatedResult<RulesetRecord>> {
    try {
      const { domain, jurisdiction, status } = params;
      let results = [...this.rulesets];
      if (domain) {
        results = results.filter((r) => r.domain === domain);
      }
      if (jurisdiction) {
        results = results.filter((r) => r.jurisdiction === jurisdiction);
      }
      if (status) {
        results = results.filter((r) => r.status === status);
      }
      return this.paginate(results, params);
    } catch (error) {
      console.error("MockAdminService.listRulesets failed, returning fallback data", error);
      return this.paginate([...this.rulesets], params);
    }
  }

  async uploadRuleset(
    file: File,
    domain: string,
    jurisdiction: string,
    rulesetVersion: string,
    rulebookVersion: string,
    effectiveFrom?: string,
    effectiveTo?: string,
    notes?: string
  ): Promise<MutationResult<RulesetUploadResult>> {
    // Simulate file reading and validation
    const text = await file.text();
    let rulesJson: unknown[];
    try {
      rulesJson = JSON.parse(text);
    } catch (e) {
      return { success: false, message: `Invalid JSON: ${e instanceof Error ? e.message : String(e)}` };
    }

    // Mock validation
    const validation = {
      valid: true,
      ruleCount: Array.isArray(rulesJson) ? rulesJson.length : 0,
      errors: [] as string[],
      warnings: [] as string[],
      metadata: {
        domains: [domain],
        jurisdictions: [jurisdiction],
      },
    };

    if (!Array.isArray(rulesJson)) {
      validation.valid = false;
      validation.errors.push("Ruleset must be an array of rules");
    }

    if (validation.ruleCount === 0) {
      validation.warnings.push("No rules found in file");
    }

    // Create new ruleset
    const newRuleset: RulesetRecord = {
      id: `ruleset-${this.rulesets.length + 1}`,
      domain,
      jurisdiction,
      rulesetVersion,
      rulebookVersion,
      filePath: `rules/${domain}/${domain}-${rulebookVersion.toLowerCase().replace(/:/g, "-")}-v${rulesetVersion}.json`,
      status: "draft",
      checksumMd5: "mock-checksum-" + Math.random().toString(36).slice(2, 10),
      ruleCount: validation.ruleCount,
      createdAt: now(),
      createdBy: "current-user",
      effectiveFrom,
      effectiveTo,
      notes,
    };

    this.rulesets.unshift(newRuleset);

    // Create audit log
    this.rulesetAudit.unshift({
      id: `audit-${this.rulesetAudit.length + 1}`,
      rulesetId: newRuleset.id,
      action: "upload",
      actorId: "current-user",
      createdAt: now(),
      detail: { validation },
    });

    if (validation.valid) {
      this.rulesetAudit.unshift({
        id: `audit-${this.rulesetAudit.length + 1}`,
        rulesetId: newRuleset.id,
        action: "validate",
        actorId: "current-user",
        createdAt: now(),
        detail: { validation },
      });
    }

    return {
      success: true,
      data: {
        ruleset: newRuleset,
        validation,
      },
      message: validation.valid ? "Ruleset uploaded successfully" : "Ruleset uploaded with validation warnings",
    };
  }

  async publishRuleset(id: string): Promise<MutationResult<RulesetRecord>> {
    const ruleset = this.rulesets.find((r) => r.id === id);
    if (!ruleset) {
      return { success: false, message: "Ruleset not found" };
    }

    if (ruleset.status === "active") {
      return { success: false, message: "Ruleset is already active" };
    }

    // Archive existing active for same domain/jurisdiction
    const existingActive = this.rulesets.find(
      (r) => r.domain === ruleset.domain && r.jurisdiction === ruleset.jurisdiction && r.status === "active" && r.id !== id
    );
    if (existingActive) {
      existingActive.status = "archived";
      this.rulesetAudit.unshift({
        id: `audit-${this.rulesetAudit.length + 1}`,
        rulesetId: existingActive.id,
        action: "archive",
        actorId: "current-user",
        createdAt: now(),
        detail: { replacedBy: id },
      });
    }

    // Publish new ruleset
    ruleset.status = "active";
    ruleset.publishedAt = now();
    ruleset.publishedBy = "current-user";

    this.rulesetAudit.unshift({
      id: `audit-${this.rulesetAudit.length + 1}`,
      rulesetId: ruleset.id,
      action: "publish",
      actorId: "current-user",
      createdAt: now(),
      detail: { replacedRulesetId: existingActive?.id },
    });

    return { success: true, data: clone(ruleset), message: "Ruleset published successfully" };
  }

  async rollbackRuleset(id: string): Promise<MutationResult<RulesetRecord>> {
    const targetRuleset = this.rulesets.find((r) => r.id === id);
    if (!targetRuleset) {
      return { success: false, message: "Ruleset not found" };
    }

    const currentActive = this.rulesets.find(
      (r) => r.domain === targetRuleset.domain && r.jurisdiction === targetRuleset.jurisdiction && r.status === "active"
    );

    if (currentActive && currentActive.id === targetRuleset.id) {
      return { success: false, message: "Ruleset is already active" };
    }

    // Archive current active
    if (currentActive) {
      currentActive.status = "archived";
      this.rulesetAudit.unshift({
        id: `audit-${this.rulesetAudit.length + 1}`,
        rulesetId: currentActive.id,
        action: "archive",
        actorId: "current-user",
        createdAt: now(),
        detail: { rolledBackTo: id },
      });
    }

    // Activate target
    targetRuleset.status = "active";
    targetRuleset.publishedAt = now();
    targetRuleset.publishedBy = "current-user";

    this.rulesetAudit.unshift({
      id: `audit-${this.rulesetAudit.length + 1}`,
      rulesetId: targetRuleset.id,
      action: "rollback",
      actorId: "current-user",
      createdAt: now(),
      detail: { replacedRulesetId: currentActive?.id },
    });

    return { success: true, data: clone(targetRuleset), message: "Ruleset rolled back successfully" };
  }

  async getActiveRuleset(domain: string, jurisdiction: string, includeContent?: boolean): Promise<ActiveRulesetResult> {
    const ruleset = this.rulesets.find(
      (r) => r.domain === domain && r.jurisdiction === jurisdiction && r.status === "active"
    );

    if (!ruleset) {
      throw new Error(`No active ruleset found for domain=${domain}, jurisdiction=${jurisdiction}`);
    }

    return {
      ruleset: clone(ruleset),
      signedUrl: includeContent ? `https://storage.example.com/signed-url/${ruleset.filePath}` : undefined,
      content: includeContent ? [] : undefined, // Mock empty array for content
    };
  }

  async getRulesetAudit(id: string): Promise<RulesetAuditLog[]> {
    return clone(this.rulesetAudit.filter((log) => log.rulesetId === id));
  }

  async recordAdminAudit(event: Omit<AdminAuditEvent, "id" | "createdAt">): Promise<MutationResult> {
    const entry: AdminAuditEvent = {
      id: `audit-${this.adminAudit.length + 1}`,
      createdAt: now(),
      ...event,
    };
    this.adminAudit.unshift(entry);
    return { success: true };
  }

  async listAdminAuditLog(params: { page: number; pageSize: number }): Promise<PaginatedResult<AdminAuditEvent>> {
    return this.paginate(this.adminAudit, params);
  }
}

