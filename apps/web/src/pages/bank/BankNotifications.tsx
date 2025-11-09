import * as React from "react";
import { useNavigate } from "react-router-dom";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { NotificationList, type Notification } from "@/components/notifications/NotificationItem";

// Mock notifications for bank dashboard
const mockBankNotifications: Notification[] = [
  {
    id: 1,
    title: "Approval Required",
    message: "LC-BNK-2024-001 requires your approval at Analyst Review stage.",
    type: "approval",
    timestamp: "15 minutes ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=approvals&lc=LC-BNK-2024-001",
    badge: "Pending",
    action: {
      label: "Review Approval",
      action: () => {},
    },
  },
  {
    id: 2,
    title: "Discrepancy Assigned",
    message: "You have been assigned to resolve discrepancy in LC-BNK-2024-002.",
    type: "discrepancy",
    timestamp: "1 hour ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=discrepancies&lc=LC-BNK-2024-002",
    badge: "High Priority",
    action: {
      label: "View Discrepancy",
      action: () => {},
      variant: "destructive",
    },
  },
  {
    id: 3,
    title: "Validation Complete",
    message: "LC-BNK-2024-003 validation completed successfully with no issues.",
    type: "success",
    timestamp: "3 hours ago",
    read: false,
    link: "/lcopilot/bank-dashboard?tab=results&lc=LC-BNK-2024-003",
    action: {
      label: "View Results",
      action: () => {},
    },
  },
  {
    id: 4,
    title: "Policy Update",
    message: "New UCP600 ruleset v1.0.0 has been published and is now active.",
    type: "info",
    timestamp: "1 day ago",
    read: true,
    link: "/lcopilot/bank-dashboard?tab=policy",
    action: {
      label: "View Policy",
      action: () => {},
    },
  },
];

export function BankNotificationsView({ embedded = false }: { embedded?: boolean }) {
  const [notifications, setNotifications] = React.useState(mockBankNotifications);
  const navigate = useNavigate();

  const handleMarkAsRead = (id: string | number) => {
    setNotifications((prev) => prev.map((n) => (n.id === id ? { ...n, read: true } : n)));
    // In a real app, call API to mark as read
  };

  const handleDismiss = (id: string | number) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
    // In a real app, call API to dismiss
  };

  const handleMarkAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    // In a real app, call API to mark all as read
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Notifications</h2>
          <p className="text-muted-foreground">Stay updated on approvals, discrepancies, and system updates.</p>
        </div>
      </div>

      <Card>
        <CardContent className="pt-6">
          <NotificationList
            notifications={notifications}
            onMarkAsRead={handleMarkAsRead}
            onDismiss={handleDismiss}
            onMarkAllAsRead={handleMarkAllAsRead}
            showHeader={true}
          />
        </CardContent>
      </Card>
    </div>
  );
}

