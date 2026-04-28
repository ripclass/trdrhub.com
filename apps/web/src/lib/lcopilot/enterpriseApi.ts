/**
 * Enterprise tier API client — Phase A10.
 */

import { api } from "@/api/client";

export interface ActivityKPIs {
  label: string;
  count: number;
  description: string | null;
}

export interface GroupOverview {
  company_id: string;
  activities: string[];
  total_validations: number;
  active_lcs: number;
  open_discrepancies: number;
  open_repaper_requests: number;
  suppliers: ActivityKPIs;
  foreign_buyers: ActivityKPIs;
  services_clients: ActivityKPIs;
  billable_unbilled_hours: number;
  members_active: number;
  generated_at: string;
}

export interface AuditLogEntry {
  id: string;
  user_id: string | null;
  user_email: string | null;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  timestamp: string;
  ip_address: string | null;
  metadata: Record<string, unknown> | null;
}

export interface AuditLogResponse {
  entries: AuditLogEntry[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface MyRoleResponse {
  role: string | null;
  permissions: string[];
}

export async function getGroupOverview(): Promise<GroupOverview> {
  const { data } = await api.get<GroupOverview>(
    "/api/enterprise/group-overview",
  );
  return data;
}

export async function getAuditLog(opts?: {
  daysBack?: number;
  action?: string;
  userId?: string;
  page?: number;
  pageSize?: number;
}): Promise<AuditLogResponse> {
  const params = new URLSearchParams();
  if (opts?.daysBack != null) params.set("days_back", String(opts.daysBack));
  if (opts?.action) params.set("action", opts.action);
  if (opts?.userId) params.set("user_id", opts.userId);
  if (opts?.page != null) params.set("page", String(opts.page));
  if (opts?.pageSize != null) params.set("page_size", String(opts.pageSize));
  const query = params.toString();
  const path = query ? `/api/enterprise/audit-log?${query}` : "/api/enterprise/audit-log";
  const { data } = await api.get<AuditLogResponse>(path);
  return data;
}

export async function getMyRole(): Promise<MyRoleResponse> {
  const { data } = await api.get<MyRoleResponse>("/api/enterprise/my-role");
  return data;
}
