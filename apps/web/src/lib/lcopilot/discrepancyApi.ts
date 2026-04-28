/**
 * Discrepancy + re-papering API client — Phase A2.
 *
 * Thin wrappers over /api/discrepancies/{id}/* and /api/repaper/{id}/*.
 * The IDs accepted here are the persisted Discrepancy.id UUIDs that
 * ride on IssueCard.id (option B persistence — see
 * apps/api/app/services/finding_persistence.py).
 */

import { api } from "@/api/client";

export interface DiscrepancyComment {
  id: string;
  body: string;
  source: "user" | "recipient" | "system";
  author_user_id: string | null;
  author_email: string | null;
  author_display_name: string | null;
  created_at: string;
}

export interface DiscrepancyRead {
  id: string;
  validation_session_id: string;
  state: string;
  severity: string;
  description: string;
  owner_user_id: string | null;
  acknowledged_at: string | null;
  resolved_at: string | null;
  resolution_action: string | null;
  resolution_evidence_session_id: string | null;
}

export interface RepaperRead {
  id: string;
  discrepancy_id: string;
  recipient_email: string;
  recipient_display_name: string | null;
  state: string;
  message: string | null;
  access_token: string | null;
  replacement_session_id: string | null;
  created_at: string;
  opened_at: string | null;
  submitted_at: string | null;
  resolved_at: string | null;
}

export type DiscrepancyResolveAction = "accept" | "reject" | "waive" | "resolved";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export function isPersistedDiscrepancyId(id: string | null | undefined): boolean {
  if (!id) return false;
  return UUID_RE.test(id.trim());
}

export async function listComments(
  discrepancyId: string,
): Promise<DiscrepancyComment[]> {
  const { data } = await api.get<DiscrepancyComment[]>(
    `/api/discrepancies/${discrepancyId}/comments`,
  );
  return data ?? [];
}

export async function postComment(
  discrepancyId: string,
  body: string,
): Promise<DiscrepancyComment> {
  const { data } = await api.post<DiscrepancyComment>(
    `/api/discrepancies/${discrepancyId}/comment`,
    { body },
  );
  return data;
}

export async function resolveDiscrepancy(
  discrepancyId: string,
  action: DiscrepancyResolveAction,
  note?: string,
): Promise<DiscrepancyRead> {
  const { data } = await api.post<DiscrepancyRead>(
    `/api/discrepancies/${discrepancyId}/resolve`,
    { action, note },
  );
  return data;
}

export async function requestRepaper(
  discrepancyId: string,
  payload: {
    recipient_email: string;
    recipient_display_name?: string;
    message?: string;
  },
): Promise<RepaperRead> {
  const { data } = await api.post<RepaperRead>(
    `/api/discrepancies/${discrepancyId}/repaper`,
    payload,
  );
  return data;
}
