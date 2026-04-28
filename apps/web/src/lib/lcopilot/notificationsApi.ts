/**
 * Notifications API client — Phase A3.
 *
 * Thin wrappers over /api/notifications/*. Used by the bell icon and
 * (next slice) the settings page section.
 */

import { api } from "@/api/client";

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  body: string;
  link_url: string | null;
  metadata: Record<string, unknown> | null;
  read_at: string | null;
  created_at: string;
}

export interface NotificationPreferenceEntry {
  in_app: boolean;
  email: boolean;
}

export interface NotificationPreferences {
  preferences: Record<string, NotificationPreferenceEntry>;
}

export async function listNotifications(opts?: {
  limit?: number;
  onlyUnread?: boolean;
}): Promise<NotificationItem[]> {
  const params = new URLSearchParams();
  if (opts?.limit != null) params.set("limit", String(opts.limit));
  if (opts?.onlyUnread) params.set("only_unread", "true");
  const query = params.toString();
  const path = query
    ? `/api/notifications?${query}`
    : "/api/notifications";
  const { data } = await api.get<NotificationItem[]>(path);
  return data ?? [];
}

export async function getUnreadCount(): Promise<number> {
  const { data } = await api.get<{ unread_count: number }>(
    "/api/notifications/unread-count",
  );
  return data?.unread_count ?? 0;
}

export async function markRead(id: string): Promise<NotificationItem> {
  const { data } = await api.post<NotificationItem>(
    `/api/notifications/${id}/read`,
  );
  return data;
}

export async function markAllRead(): Promise<number> {
  const { data } = await api.post<{ marked_read: number }>(
    "/api/notifications/read-all",
  );
  return data?.marked_read ?? 0;
}

export async function getPreferences(): Promise<NotificationPreferences> {
  const { data } = await api.get<NotificationPreferences>(
    "/api/notifications/preferences",
  );
  return data;
}

export async function updatePreferences(
  preferences: Record<string, NotificationPreferenceEntry>,
): Promise<NotificationPreferences> {
  const { data } = await api.put<NotificationPreferences>(
    "/api/notifications/preferences",
    { preferences },
  );
  return data;
}
