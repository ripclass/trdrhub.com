import { api } from "@/api/client";
import type { AdminService, KPIStat, OpsMetric, OpsAlert, PaginatedResult, OpsJob, TimeRange, AdminAuditEvent } from "../../types";
import type { LucideIcon } from "lucide-react";
import { Activity, Bell, ShieldCheck, Users, FileText, Layers } from "lucide-react";
import type {
  RulesetRecord,
  RulesetStatus,
  RulesetUploadResult,
  ActiveRulesetResult,
  RulesetAuditLog,
  MutationResult,
  RuleRecord,
  RuleListParams,
  RuleUpdatePayload,
  BulkSyncResult,
} from "../../types";

const KPI_ICON_MAP: Record<string, LucideIcon> = {
  "lc-volume": FileText,
  "lc-success": ShieldCheck,
  "active-companies": Users,
  "active-rulesets": Layers,
  "open-alerts": Bell,
};

/**
 * Real API implementation of AdminService that calls the backend.
 * This replaces the mock service to persist data in the database.
 */
export class ApiAdminService implements AdminService {
  // Ruleset methods
  async listRulesets(params: {
    page: number;
    pageSize: number;
    domain?: string;
    jurisdiction?: string;
    status?: RulesetStatus;
  }): Promise<PaginatedResult<RulesetRecord>> {
    try {
      const queryParams = new URLSearchParams({
        page: params.page.toString(),
        page_size: params.pageSize.toString(),
      });
      if (params.domain) queryParams.append("domain", params.domain);
      if (params.jurisdiction) queryParams.append("jurisdiction", params.jurisdiction);
      if (params.status) queryParams.append("status", params.status);

      const response = await api.get(`/admin/rulesets?${queryParams.toString()}`);
      const data = response.data;

      return {
        items: data.items.map(this.transformRuleset),
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
      };
    } catch (error: any) {
      console.error("Failed to list rulesets:", error);
      throw new Error(error?.response?.data?.detail || "Failed to load rulesets");
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
    try {
      const formData = new FormData();
      formData.append("file", file);

      const queryParams = new URLSearchParams({
        domain,
        jurisdiction,
        ruleset_version: rulesetVersion,
        rulebook_version: rulebookVersion,
      });
      if (effectiveFrom) queryParams.append("effective_from", effectiveFrom);
      if (effectiveTo) queryParams.append("effective_to", effectiveTo);
      if (notes) queryParams.append("notes", notes);

      const response = await api.post(`/admin/rulesets/upload?${queryParams.toString()}`, formData, {
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      const data = response.data;
      const importSummary = data.import_summary
        ? {
            totalRules: data.import_summary.total_rules,
            inserted: data.import_summary.inserted,
            updated: data.import_summary.updated,
            skipped: data.import_summary.skipped,
            errors: data.import_summary.errors ?? [],
            warnings: data.import_summary.warnings ?? [],
          }
        : undefined;
      return {
        success: true,
        data: {
          ruleset: this.transformRuleset(data.ruleset),
          validation: data.validation,
          importSummary,
        },
        message: "Ruleset uploaded successfully",
      };
    } catch (error: any) {
      console.error("Failed to upload ruleset:", error);
      const errorMessage =
        error?.response?.data?.detail?.message ||
        error?.response?.data?.detail ||
        "Failed to upload ruleset";
      return {
        success: false,
        message: errorMessage,
      };
    }
  }

  async publishRuleset(id: string): Promise<MutationResult<RulesetRecord>> {
    try {
      const response = await api.post(`/admin/rulesets/${id}/publish`);
      return {
        success: true,
        data: this.transformRuleset(response.data),
        message: "Ruleset published successfully",
      };
    } catch (error: any) {
      console.error("Failed to publish ruleset:", error);
      return {
        success: false,
        message: error?.response?.data?.detail || "Failed to publish ruleset",
      };
    }
  }

  async rollbackRuleset(id: string): Promise<MutationResult<RulesetRecord>> {
    try {
      const response = await api.post(`/admin/rulesets/${id}/rollback`);
      return {
        success: true,
        data: this.transformRuleset(response.data),
        message: "Ruleset rolled back successfully",
      };
    } catch (error: any) {
      console.error("Failed to rollback ruleset:", error);
      return {
        success: false,
        message: error?.response?.data?.detail || "Failed to rollback ruleset",
      };
    }
  }

  async getActiveRuleset(
    domain: string,
    jurisdiction: string,
    includeContent = false
  ): Promise<ActiveRulesetResult> {
    try {
      const queryParams = new URLSearchParams({
        domain,
        jurisdiction,
        include_content: includeContent.toString(),
      });

      const response = await api.get(`/admin/rulesets/active?${queryParams.toString()}`);
      const data = response.data;

      return {
        ruleset: this.transformRuleset(data.ruleset),
        signedUrl: data.signed_url,
        content: data.content,
      };
    } catch (error: any) {
      if (error?.response?.status === 404) {
        throw new Error(`No active ruleset found for ${domain}/${jurisdiction}`);
      }
      console.error("Failed to get active ruleset:", error);
      throw new Error(error?.response?.data?.detail || "Failed to get active ruleset");
    }
  }

  async getAllActiveRulesets(includeContent = false): Promise<ActiveRulesetResult[]> {
    try {
      const queryParams = new URLSearchParams({
        include_content: includeContent.toString(),
      });

      const response = await api.get(`/admin/rulesets/active/all?${queryParams.toString()}`);
      const data = response.data;

      return data.map((item: any) => ({
        ruleset: this.transformRuleset(item.ruleset),
        signedUrl: item.signed_url,
        content: item.content,
      }));
    } catch (error: any) {
      console.error("Failed to get all active rulesets:", error);
      throw new Error(error?.response?.data?.detail || "Failed to get all active rulesets");
    }
  }

  async getRulesetAudit(id: string): Promise<RulesetAuditLog[]> {
    try {
      const response = await api.get(`/admin/rulesets/${id}/audit`);
      return response.data.map((log: any) => ({
        id: log.id,
        rulesetId: log.ruleset_id,
        action: log.action,
        actorId: log.actor_id,
        detail: log.detail,
        createdAt: log.created_at,
      }));
    } catch (error: any) {
      console.error("Failed to get ruleset audit:", error);
      throw new Error(error?.response?.data?.detail || "Failed to get audit log");
    }
  }

  async listRules(params: RuleListParams): Promise<PaginatedResult<RuleRecord>> {
    try {
      const queryParams = new URLSearchParams({
        page: params.page.toString(),
        page_size: params.pageSize.toString(),
      });
      if (params.domain) queryParams.append("domain", params.domain);
      if (params.documentType) queryParams.append("document_type", params.documentType);
      if (params.severity) queryParams.append("severity", params.severity);
      if (params.requiresLlm !== undefined) queryParams.append("requires_llm", String(params.requiresLlm));
      if (params.isActive !== undefined) queryParams.append("is_active", String(params.isActive));
      if (params.search) queryParams.append("search", params.search);

      const response = await api.get(`/admin/rules?${queryParams.toString()}`);
      const data = response.data;
      return {
        items: data.items.map((item: any) => this.transformRuleRecord(item)),
        total: data.total,
        page: data.page,
        pageSize: data.page_size,
      };
    } catch (error: any) {
      console.error("Failed to list rules:", error);
      throw new Error(error?.response?.data?.detail || "Failed to load rules");
    }
  }

  async getRule(ruleId: string): Promise<RuleRecord> {
    try {
      const response = await api.get(`/admin/rules/${ruleId}`);
      return this.transformRuleRecord(response.data);
    } catch (error: any) {
      console.error("Failed to fetch rule:", error);
      throw new Error(error?.response?.data?.detail || "Failed to retrieve rule");
    }
  }

  async updateRule(ruleId: string, payload: RuleUpdatePayload): Promise<RuleRecord> {
    try {
      const response = await api.patch(`/admin/rules/${ruleId}`, payload);
      return this.transformRuleRecord(response.data);
    } catch (error: any) {
      console.error("Failed to update rule:", error);
      throw new Error(error?.response?.data?.detail || "Failed to update rule");
    }
  }

  async deleteRule(ruleId: string, hard = false): Promise<MutationResult> {
    try {
      await api.delete(`/admin/rules/${ruleId}`, {
        params: { hard: hard ? "true" : "false" },
      });
      return { success: true, message: "Rule removed" };
    } catch (error: any) {
      console.error("Failed to delete rule:", error);
      return {
        success: false,
        message: error?.response?.data?.detail || "Failed to delete rule",
      };
    }
  }

  async bulkSyncRules(params: { rulesetId?: string; includeInactive?: boolean } = {}): Promise<BulkSyncResult> {
    try {
      const payload =
        params.rulesetId || params.includeInactive
          ? {
              ruleset_id: params.rulesetId,
              include_inactive: params.includeInactive ?? false,
            }
          : undefined;

      const response = await api.post("/admin/rules/bulk-sync", payload, {
        params: {
          ruleset_id: params.rulesetId,
          include_inactive: params.includeInactive,
        },
      });
      const data = response.data;
      return {
        items: data.items.map(
          (item: any): BulkSyncResult["items"][number] => ({
            rulesetId: item.ruleset_id,
            status: item.status,
            domain: item.domain,
            jurisdiction: item.jurisdiction,
            summary: item.summary ?? {},
          })
        ),
      };
    } catch (error: any) {
      console.error("Failed to run rules bulk sync:", error);
      throw new Error(error?.response?.data?.detail || "Failed to sync rules");
    }
  }

  /**
   * Transform backend ruleset format to frontend format
   */
  private transformRuleRecord(data: any): RuleRecord {
    return {
      ruleId: data.rule_id,
      ruleVersion: data.rule_version ?? undefined,
      article: data.article ?? undefined,
      version: data.version ?? undefined,
      domain: data.domain,
      jurisdiction: data.jurisdiction,
      documentType: data.document_type,
      ruleType: data.rule_type,
      severity: data.severity,
      deterministic: Boolean(data.deterministic),
      requiresLlm: Boolean(data.requires_llm),
      title: data.title,
      reference: data.reference ?? undefined,
      description: data.description ?? undefined,
      conditions: data.conditions ?? [],
      expectedOutcome: data.expected_outcome ?? {},
      tags: data.tags ?? [],
      metadata: data.metadata ?? null,
      checksum: data.checksum,
      rulesetId: data.ruleset_id ?? undefined,
      rulesetVersion: data.ruleset_version ?? undefined,
      isActive: Boolean(data.is_active),
      archivedAt: data.archived_at ?? undefined,
      createdAt: data.created_at,
      updatedAt: data.updated_at,
    };
  }

  private transformRuleset(data: any): RulesetRecord {
    return {
      id: data.id,
      domain: data.domain,
      jurisdiction: data.jurisdiction,
      rulesetVersion: data.ruleset_version,
      rulebookVersion: data.rulebook_version,
      filePath: data.file_path,
      status: data.status as RulesetStatus,
      effectiveFrom: data.effective_from,
      effectiveTo: data.effective_to,
      checksumMd5: data.checksum_md5,
      ruleCount: data.rule_count,
      createdBy: data.created_by,
      createdAt: data.created_at,
      publishedBy: data.published_by,
      publishedAt: data.published_at,
      notes: data.notes,
    };
  }

  async getDashboardStats(range: TimeRange): Promise<KPIStat[]> {
    try {
      const response = await api.get(`/admin/dashboard/kpis`, {
        params: { range },
      });
      const stats = response.data?.stats ?? [];
      return stats.map((stat: any) => {
        const Icon = KPI_ICON_MAP[stat.id] ?? Activity;
        return {
          id: stat.id,
          label: stat.label,
          value: stat.value,
          change: stat.change ?? 0,
          changeLabel: stat.changeLabel ?? "",
          changeDirection: stat.changeDirection ?? "flat",
          icon: Icon,
          href: stat.href,
          emphasis: Boolean(stat.emphasis),
        };
      });
    } catch (error) {
      console.error("Failed to fetch dashboard stats", error);
      throw new Error("Unable to load dashboard metrics");
    }
  }

  async getOpsMetrics(range: TimeRange): Promise<OpsMetric[]> {
    try {
      const timeRange = range === "24h" ? "24h" : "7d";
      const response = await api.get("/admin/jobs/queue/stats", {
        params: { time_range: timeRange },
      });
      const data = response.data ?? {};
      const metrics: OpsMetric[] = [
        {
          id: "total-jobs",
          name: "Jobs processed",
          value: data.total_jobs ?? 0,
          change: 0,
          trend: "stable",
        },
        {
          id: "queue-depth",
          name: "Queue depth",
          value: data.queue_depth ?? 0,
          change: 0,
          trend: "stable",
        },
        {
          id: "avg-duration",
          name: "Avg. processing time (ms)",
          value: data.avg_processing_time_ms ?? 0,
          change: 0,
          trend: "stable",
        },
      ];
      return metrics;
    } catch (error) {
      console.error("Failed to fetch ops metrics", error);
      throw new Error("Unable to load ops metrics");
    }
  }

  async listJobs(params: { page: number; pageSize: number; status?: string[]; search?: string }): Promise<PaginatedResult<OpsJob>> {
    const offset = (params.page - 1) * params.pageSize;
    try {
      const response = await api.get("/admin/jobs/queue", {
        params: {
          limit: params.pageSize,
          offset,
          status: params.status?.[0],
          search: params.search,
        },
      });
      const data = response.data;
      return {
        items: data.items ?? [],
        total: data.total ?? 0,
        page: data.page ?? params.page,
        pageSize: data.size ?? params.pageSize,
      };
    } catch (error) {
      console.error("Failed to list jobs", error);
      throw new Error("Unable to load jobs");
    }
  }

  async retryJob(id: string): Promise<MutationResult> {
    try {
      await api.post(`/admin/jobs/queue/${id}/retry`, null, {
        params: { reason: "Retry via admin console" },
      });
      return { success: true, message: "Job re-queued" };
    } catch (error: any) {
      console.error("Failed to retry job", error);
      return { success: false, message: error?.response?.data?.detail ?? "Failed to retry job" };
    }
  }

  async cancelJob(id: string): Promise<MutationResult> {
    try {
      await api.post(`/admin/jobs/queue/${id}/cancel`, null, {
        params: { reason: "Cancelled via admin console" },
      });
      return { success: true, message: "Job cancelled" };
    } catch (error: any) {
      console.error("Failed to cancel job", error);
      return { success: false, message: error?.response?.data?.detail ?? "Failed to cancel job" };
    }
  }

  async listAlerts(params: { page: number; pageSize: number; severity?: OpsAlert["severity"][]; status?: "active" | "acknowledged" | "resolved" }): Promise<PaginatedResult<OpsAlert>> {
    try {
      const response = await api.get("/admin/ops/system-alerts", {
        params: {
          page: params.page,
          page_size: params.pageSize,
          severity: params.severity?.[0],
          status: params.status,
        },
      });
      const data = response.data;
      return {
        items: (data.items ?? []) as OpsAlert[],
        total: data.total ?? 0,
        page: data.page ?? params.page,
        pageSize: data.page_size ?? params.pageSize,
      };
    } catch (error) {
      console.error("Failed to fetch alerts", error);
      throw new Error("Unable to load alerts");
    }
  }

  async acknowledgeAlert(id: string): Promise<MutationResult> {
    try {
      await api.post(`/admin/ops/system-alerts/${id}/acknowledge`);
      return { success: true, message: "Alert acknowledged" };
    } catch (error: any) {
      console.error("Failed to acknowledge alert", error);
      return { success: false, message: error?.response?.data?.detail ?? "Unable to acknowledge alert" };
    }
  }

  async snoozeAlert(id: string, minutes: number): Promise<MutationResult> {
    try {
      await api.post(`/admin/ops/system-alerts/${id}/snooze`, null, {
        params: { minutes },
      });
      return { success: true, message: `Alert snoozed for ${minutes} minutes` };
    } catch (error: any) {
      console.error("Failed to snooze alert", error);
      return { success: false, message: error?.response?.data?.detail ?? "Unable to snooze alert" };
    }
  }
  async listAuditLogs(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listApprovalRequests(): Promise<any> {
    throw new Error("Not implemented");
  }
  async resolveApproval(): Promise<any> {
    throw new Error("Not implemented");
  }
  async getComplianceSummary(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async listUsers(): Promise<any> {
    throw new Error("Not implemented");
  }
  async inviteUser(): Promise<any> {
    throw new Error("Not implemented");
  }
  async disableUser(): Promise<any> {
    throw new Error("Not implemented");
  }
  async updateUserRole(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listRoles(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async listApiKeys(): Promise<any> {
    throw new Error("Not implemented");
  }
  async createApiKey(): Promise<any> {
    throw new Error("Not implemented");
  }
  async rotateApiKey(): Promise<any> {
    throw new Error("Not implemented");
  }
  async revokeApiKey(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listSessions(): Promise<any> {
    throw new Error("Not implemented");
  }
  async revokeSession(): Promise<any> {
    throw new Error("Not implemented");
  }
  async getBillingSummary(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listBillingPlans(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async updateBillingPlan(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listBillingAdjustments(): Promise<any> {
    throw new Error("Not implemented");
  }
  async addBillingAdjustment(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listBillingDisputes(): Promise<any> {
    throw new Error("Not implemented");
  }
  async resolveDispute(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listPartners(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async setPartnerStatus(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listConnectors(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async updateConnector(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listWebhookDeliveries(): Promise<any> {
    throw new Error("Not implemented");
  }
  async redeliverWebhook(): Promise<any> {
    throw new Error("Not implemented");
  }
  async rotateWebhookSecret(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listPrompts(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async publishPromptVersion(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listLLMBudgets(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async updateLLMBudget(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listEvaluationRuns(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listResidencyPolicies(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async listRetentionSchedules(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async runRetentionSchedule(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listLegalHolds(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async createLegalHold(): Promise<any> {
    throw new Error("Not implemented");
  }
  async releaseLegalHold(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listFeatureFlags(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async setFeatureFlagStatus(): Promise<any> {
    throw new Error("Not implemented");
  }
  async updateFeatureFlagTargeting(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listReleases(): Promise<any> {
    throw new Error("Not implemented");
  }
  async getSettings(): Promise<any> {
    // Return default settings for now (backend endpoint not implemented yet)
    return {
      branding: {
        primaryColor: "#3b82f6",
        supportEmail: "support@trdrhub.com",
      },
      authentication: {
        passwordPolicy: "Minimum 8 characters",
        mfaEnforced: false,
        ssoEnabled: false,
        sessionTimeoutMinutes: 60,
      },
      notifications: {
        dailySummary: true,
        weeklyInsights: true,
        criticalAlerts: true,
        digestEmail: "admin@trdrhub.com",
      },
    };
  }
  
  async updateSettings(settings: Partial<any>): Promise<MutationResult<any>> {
    // Stub implementation (backend endpoint not implemented yet)
    return {
      success: true,
      data: settings,
      message: "Settings updated (stub - backend not implemented)",
    };
  }

  async recordAdminAudit(event: Omit<AdminAuditEvent, "id" | "createdAt">): Promise<MutationResult> {
    try {
      await api.post("/admin/audit/log-action", {
        section: event.section,
        action: event.action,
        actor: event.actor,
        actorRole: event.actorRole,
        entityId: event.entityId,
        metadata: event.metadata,
      });
      return { success: true, message: "Recorded" };
    } catch (error) {
      console.error("Failed to record admin audit", error);
      return { success: false, message: "Unable to record audit entry" };
    }
  }

  async listAdminAuditLog(params: { page: number; pageSize: number }): Promise<PaginatedResult<AdminAuditEvent>> {
    try {
      const response = await api.get("/admin/dashboard/activity", {
        params: { limit: params.pageSize },
      });
      const items: AdminAuditEvent[] = (response.data?.items ?? []).map((item: any) => ({
        id: item.id,
        actor: item.actor,
        actorRole: "admin",
        action: item.action,
        section: "overview",
        createdAt: item.createdAt,
      }));
      return {
        items,
        total: items.length,
        page: params.page,
        pageSize: params.pageSize,
      };
    } catch (error) {
      console.error("Failed to load admin audit log", error);
      return {
        items: [],
        total: 0,
        page: params.page,
        pageSize: params.pageSize,
      };
    }
  }
}

