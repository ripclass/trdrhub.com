import { api } from "@/api/client";
import type { AdminService } from "../../types";
import type {
  RulesetRecord,
  RulesetStatus,
  RulesetUploadResult,
  ActiveRulesetResult,
  RulesetAuditLog,
  MutationResult,
  PaginatedResult,
} from "../../types";

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
      return {
        success: true,
        data: {
          ruleset: this.transformRuleset(data.ruleset),
          validation: data.validation,
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

  /**
   * Transform backend ruleset format to frontend format
   */
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

  // Stub implementations for other AdminService methods
  // These can be implemented later as needed
  async getDashboardStats(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async getOpsMetrics(): Promise<any[]> {
    throw new Error("Not implemented");
  }
  async listJobs(): Promise<any> {
    throw new Error("Not implemented");
  }
  async retryJob(): Promise<any> {
    throw new Error("Not implemented");
  }
  async cancelJob(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listAlerts(): Promise<any> {
    throw new Error("Not implemented");
  }
  async acknowledgeAlert(): Promise<any> {
    throw new Error("Not implemented");
  }
  async snoozeAlert(): Promise<any> {
    throw new Error("Not implemented");
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
  async recordAdminAudit(): Promise<any> {
    throw new Error("Not implemented");
  }
  async listAdminAuditLog(): Promise<any> {
    throw new Error("Not implemented");
  }
}

