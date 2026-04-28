/**
 * NotificationBell — header bell icon with unread badge + dropdown.
 *
 * Polls the unread-count endpoint every 60s when the dropdown is
 * closed. Opening the dropdown fetches the recent list. Clicking a
 * notification marks it read + navigates to its link_url.
 *
 * Self-suppresses when isNotificationsEnabled() returns false so the
 * DashboardLayout can include it unconditionally.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { Bell, Check } from "lucide-react";
import { isNotificationsEnabled } from "@/lib/lcopilot/featureFlags";
import {
  getUnreadCount,
  listNotifications,
  markAllRead,
  markRead,
  type NotificationItem,
} from "@/lib/lcopilot/notificationsApi";

const POLL_INTERVAL_MS = 60_000;
const LIST_LIMIT = 10;

function formatRelative(iso: string): string {
  try {
    const ms = Date.now() - new Date(iso).getTime();
    if (ms < 60_000) return "just now";
    const minutes = Math.round(ms / 60_000);
    if (minutes < 60) return `${minutes}m ago`;
    const hours = Math.round(minutes / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.round(hours / 24);
    return `${days}d ago`;
  } catch {
    return "";
  }
}

export function NotificationBell() {
  const [enabled] = useState(() => isNotificationsEnabled());
  const [open, setOpen] = useState(false);
  const [unread, setUnread] = useState<number>(0);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const fetchUnread = useCallback(async () => {
    if (!enabled) return;
    try {
      const n = await getUnreadCount();
      setUnread(n);
    } catch {
      // Silent — auth-redirect handlers in api/client will deal with 401s
    }
  }, [enabled]);

  const fetchItems = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const rows = await listNotifications({ limit: LIST_LIMIT });
      setItems(rows);
      setUnread(rows.filter((r) => !r.read_at).length);
    } catch (err) {
      setError((err as Error).message ?? "Failed to load notifications");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    if (!enabled) return;
    void fetchUnread();
    pollRef.current = window.setInterval(() => {
      if (!open) void fetchUnread();
    }, POLL_INTERVAL_MS);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, [enabled, open, fetchUnread]);

  useEffect(() => {
    if (open) void fetchItems();
  }, [open, fetchItems]);

  const handleMarkAll = useCallback(async () => {
    if (unread === 0) return;
    try {
      await markAllRead();
      setItems((prev) => prev.map((r) => ({ ...r, read_at: r.read_at ?? new Date().toISOString() })));
      setUnread(0);
    } catch (err) {
      setError((err as Error).message ?? "Failed to mark read");
    }
  }, [unread]);

  const handleItemClick = useCallback(
    async (item: NotificationItem) => {
      try {
        if (!item.read_at) {
          await markRead(item.id);
          setItems((prev) =>
            prev.map((r) =>
              r.id === item.id
                ? { ...r, read_at: new Date().toISOString() }
                : r,
            ),
          );
          setUnread((u) => Math.max(0, u - 1));
        }
      } catch {
        // ignore — navigation still happens via the Link
      }
      setOpen(false);
    },
    [],
  );

  if (!enabled) return null;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="relative"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 h-4 min-w-[1rem] rounded-full bg-rose-500 text-[10px] font-semibold text-white flex items-center justify-center px-1">
              {unread > 9 ? "9+" : unread}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-96 p-0">
        <div className="flex items-center justify-between border-b px-3 py-2">
          <h3 className="text-sm font-semibold">Notifications</h3>
          <Button
            size="sm"
            variant="ghost"
            disabled={unread === 0}
            onClick={handleMarkAll}
            className="text-xs h-6"
          >
            <Check className="w-3.5 h-3.5 mr-1" />
            Mark all read
          </Button>
        </div>

        <div className="max-h-96 overflow-y-auto">
          {loading && (
            <p className="px-3 py-4 text-xs text-muted-foreground">Loading…</p>
          )}
          {!loading && items.length === 0 && !error && (
            <p className="px-3 py-6 text-center text-xs text-muted-foreground">
              No notifications yet.
            </p>
          )}
          {error && (
            <p className="px-3 py-4 text-xs text-rose-600">{error}</p>
          )}

          {items.length > 0 && (
            <ul className="divide-y">
              {items.map((item) => {
                const unreadItem = !item.read_at;
                const inner = (
                  <div className="flex items-start gap-2 px-3 py-2">
                    <span
                      className={`mt-1 h-2 w-2 flex-shrink-0 rounded-full ${
                        unreadItem ? "bg-rose-500" : "bg-transparent"
                      }`}
                      aria-hidden="true"
                    />
                    <div className="min-w-0 flex-1">
                      <p
                        className={`text-sm ${
                          unreadItem ? "font-semibold" : "font-normal"
                        }`}
                      >
                        {item.title}
                      </p>
                      <p className="text-xs text-muted-foreground line-clamp-2">
                        {item.body}
                      </p>
                      <p className="mt-0.5 text-[10px] uppercase tracking-wide text-muted-foreground">
                        {formatRelative(item.created_at)}
                      </p>
                    </div>
                  </div>
                );
                return (
                  <li key={item.id}>
                    {item.link_url ? (
                      <Link
                        to={item.link_url}
                        onClick={() => handleItemClick(item)}
                        className="block hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
                      >
                        {inner}
                      </Link>
                    ) : (
                      <button
                        type="button"
                        onClick={() => handleItemClick(item)}
                        className="block w-full text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
                      >
                        {inner}
                      </button>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="border-t px-3 py-2 text-right">
          <Link
            to="/settings/notifications"
            onClick={() => setOpen(false)}
            className="text-xs text-muted-foreground hover:text-foreground"
          >
            Notification settings →
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  );
}
