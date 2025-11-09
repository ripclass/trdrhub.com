import * as React from "react";
import { Bell, CheckCircle2, AlertTriangle, Info, X, ArrowRight, FileCheck, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { useNavigate } from "react-router-dom";

export type NotificationType = "success" | "warning" | "info" | "error" | "approval" | "discrepancy";

export type NotificationAction = {
  label: string;
  action: () => void;
  variant?: "default" | "outline" | "destructive" | "secondary";
};

export interface Notification {
  id: string | number;
  title: string;
  message: string;
  type: NotificationType;
  timestamp: string;
  read?: boolean;
  action?: NotificationAction;
  link?: string; // Deep link to related resource
  badge?: string | number; // Badge count or text
}

interface NotificationItemProps {
  notification: Notification;
  onMarkAsRead?: (id: string | number) => void;
  onDismiss?: (id: string | number) => void;
  embedded?: boolean;
}

const typeConfig: Record<NotificationType, { icon: React.ComponentType<{ className?: string }>; color: string; bgColor: string }> = {
  success: { icon: CheckCircle2, color: "text-success", bgColor: "bg-success/10" },
  warning: { icon: AlertTriangle, color: "text-warning", bgColor: "bg-warning/10" },
  info: { icon: Info, color: "text-info", bgColor: "bg-info/10" },
  error: { icon: AlertCircle, color: "text-destructive", bgColor: "bg-destructive/10" },
  approval: { icon: FileCheck, color: "text-primary", bgColor: "bg-primary/10" },
  discrepancy: { icon: AlertTriangle, color: "text-warning", bgColor: "bg-warning/10" },
};

export function NotificationItem({ notification, onMarkAsRead, onDismiss, embedded = false }: NotificationItemProps) {
  const navigate = useNavigate();
  const config = typeConfig[notification.type];
  const Icon = config.icon;

  const handleClick = () => {
    if (notification.link) {
      navigate(notification.link);
    }
    if (!notification.read && onMarkAsRead) {
      onMarkAsRead(notification.id);
    }
  };

  const handleAction = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (notification.action) {
      notification.action.action();
    }
    if (!notification.read && onMarkAsRead) {
      onMarkAsRead(notification.id);
    }
  };

  const handleDismiss = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onDismiss) {
      onDismiss(notification.id);
    }
  };

  return (
    <div
      className={cn(
        "p-3 rounded-lg border transition-all cursor-pointer hover:bg-muted/50",
        notification.read ? "border-border/50 opacity-75" : "border-border bg-background",
        notification.link && "hover:border-primary/50"
      )}
      onClick={handleClick}
    >
      <div className="flex items-start gap-3">
        <div className={cn("p-1.5 rounded-full flex-shrink-0", config.bgColor)}>
          <Icon className={cn("w-4 h-4", config.color)} />
        </div>
        <div className="flex-1 min-w-0 space-y-2">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <h4 className={cn("font-medium text-sm", notification.read ? "text-muted-foreground" : "text-foreground")}>
                  {notification.title}
                </h4>
                {!notification.read && (
                  <Badge variant="default" className="h-4 px-1.5 text-xs">
                    New
                  </Badge>
                )}
                {notification.badge && (
                  <Badge variant="secondary" className="h-4 px-1.5 text-xs">
                    {notification.badge}
                  </Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground mt-1">{notification.message}</p>
              <p className="text-xs text-muted-foreground mt-1">{notification.timestamp}</p>
            </div>
            {onDismiss && (
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 p-0 flex-shrink-0"
                onClick={handleDismiss}
              >
                <X className="h-3 w-3" />
              </Button>
            )}
          </div>
          {notification.action && (
            <div className="flex items-center gap-2 pt-1">
              <Button
                size="sm"
                variant={notification.action.variant || "outline"}
                className="h-7 text-xs"
                onClick={handleAction}
              >
                {notification.action.label}
                <ArrowRight className="h-3 w-3 ml-1" />
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface NotificationListProps {
  notifications: Notification[];
  onMarkAsRead?: (id: string | number) => void;
  onDismiss?: (id: string | number) => void;
  onMarkAllAsRead?: () => void;
  embedded?: boolean;
  showHeader?: boolean;
}

export function NotificationList({
  notifications,
  onMarkAsRead,
  onDismiss,
  onMarkAllAsRead,
  embedded = false,
  showHeader = true,
}: NotificationListProps) {
  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <div className="space-y-4">
      {showHeader && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            <h3 className="font-semibold">Notifications</h3>
            {unreadCount > 0 && (
              <Badge variant="default" className="h-5 px-2">
                {unreadCount}
              </Badge>
            )}
          </div>
          {onMarkAllAsRead && unreadCount > 0 && (
            <Button variant="ghost" size="sm" onClick={onMarkAllAsRead} className="text-xs">
              Mark all as read
            </Button>
          )}
        </div>
      )}
      <div className="space-y-2">
        {notifications.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Bell className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>No notifications</p>
          </div>
        ) : (
          notifications.map((notification) => (
            <NotificationItem
              key={notification.id}
              notification={notification}
              onMarkAsRead={onMarkAsRead}
              onDismiss={onDismiss}
              embedded={embedded}
            />
          ))
        )}
      </div>
    </div>
  );
}

