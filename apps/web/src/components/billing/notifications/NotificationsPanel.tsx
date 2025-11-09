/**
 * Notifications Panel - Configuration and delivery monitoring
 * Restricted to Admin users only
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts';
import {
  Bell,
  Mail,
  MessageSquare,
  Smartphone,
  Webhook,
  Settings,
  TestTube,
  Plus,
  Edit,
  Trash2,
  Send,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  TrendingUp,
  Activity,
  Shield
} from 'lucide-react';
import { format, subDays } from 'date-fns';

// Hooks and types
import {
  useNotificationChannels,
  useNotificationStats,
  useNotificationHistory,
  useCreateNotificationChannel,
  useUpdateNotificationChannel,
  useDeleteNotificationChannel,
  useTestNotificationChannel,
  useSendTestNotification
} from '@/hooks/useNotifications';
import {
  NotificationType,
  NotificationStatus,
  NotificationPriority,
  NotificationTrigger,
  getNotificationStatusColor,
  getNotificationPriorityColor,
  getNotificationTypeIcon,
  formatNotificationTrigger,
  validateSlackWebhookUrl,
  validateEmailAddress
} from '@/types/notifications';
import type {
  NotificationChannel,
  CreateChannelRequest,
  NotificationFilters
} from '@/types/notifications';
import { useAuth } from '@/hooks/use-auth';

interface NotificationsPanelProps {
  className?: string;
}

export function NotificationsPanel({ className }: NotificationsPanelProps) {
  const [activeTab, setActiveTab] = useState<'channels' | 'history' | 'settings' | 'analytics'>('channels');
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);
  const [filters, setFilters] = useState<NotificationFilters>({
    page: 1,
    per_page: 25
  });

  const { user } = useAuth();

  // Role-based access control
  const canManageNotifications = user?.role === 'admin';

  // Queries
  const { data: channels, isLoading: channelsLoading, refetch: refetchChannels } = useNotificationChannels(
    { enabled: canManageNotifications }
  );

  const { data: stats, isLoading: statsLoading } = useNotificationStats(
    { time_range: '7d' },
    { enabled: canManageNotifications }
  );

  const { data: history, isLoading: historyLoading } = useNotificationHistory(
    filters,
    { enabled: canManageNotifications && activeTab === 'history' }
  );

  // Mutations
  const createChannel = useCreateNotificationChannel();
  const updateChannel = useUpdateNotificationChannel();
  const deleteChannel = useDeleteNotificationChannel();
  const testChannel = useTestNotificationChannel();
  const sendTestNotification = useSendTestNotification();

  // Access denied for unauthorized roles
  if (!canManageNotifications) {
    return (
      <div className={className}>
        <Card>
          <CardContent className="p-8 text-center">
            <Shield className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">Access Restricted</h3>
            <p className="text-muted-foreground">
              Notification management is only available to Admin users.
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  // Mock data for demonstration
  const mockChannels = [
    {
      id: '1',
      name: 'Critical Alerts Slack',
      type: NotificationType.SLACK,
      enabled: true,
      configuration: {
        webhook_url: 'https://hooks.slack.com/services/T123/B456/xyz',
        channel: '#alerts',
        username: 'LCopilot Bot'
      },
      triggers: [NotificationTrigger.ALERT_CREATED, NotificationTrigger.SYSTEM_ERROR],
      priority_filter: [NotificationPriority.CRITICAL, NotificationPriority.HIGH],
      recipients: [],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    },
    {
      id: '2',
      name: 'Admin Email Notifications',
      type: NotificationType.EMAIL,
      enabled: true,
      configuration: {
        from_email: 'noreply@lcopilot.com',
        from_name: 'LCopilot System'
      },
      triggers: [NotificationTrigger.QUOTA_BREACH, NotificationTrigger.PAYMENT_FAILED],
      priority_filter: [NotificationPriority.HIGH, NotificationPriority.CRITICAL],
      recipients: ['admin@company.com', 'alerts@company.com'],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    }
  ];

  const mockStats = {
    total_sent: 1247,
    total_delivered: 1189,
    total_failed: 58,
    delivery_rate: 95.3,
    avg_delivery_time: 2.4,
    by_type: {
      [NotificationType.EMAIL]: 756,
      [NotificationType.SLACK]: 423,
      [NotificationType.SMS]: 68
    },
    by_status: {
      [NotificationStatus.DELIVERED]: 1189,
      [NotificationStatus.FAILED]: 58
    },
    recent_activity: Array.from({ length: 7 }, (_, i) => ({
      timestamp: format(subDays(new Date(), 6 - i), 'yyyy-MM-dd'),
      type: NotificationType.EMAIL,
      status: NotificationStatus.DELIVERED,
      count: Math.floor(Math.random() * 50) + 20
    }))
  };

  const mockHistory = Array.from({ length: 20 }, (_, i) => ({
    id: `notif-${i}`,
    type: [NotificationType.EMAIL, NotificationType.SLACK, NotificationType.SMS][i % 3],
    status: [NotificationStatus.DELIVERED, NotificationStatus.FAILED, NotificationStatus.SENT][i % 3],
    priority: [NotificationPriority.HIGH, NotificationPriority.NORMAL, NotificationPriority.CRITICAL][i % 3],
    trigger: [NotificationTrigger.ALERT_CREATED, NotificationTrigger.QUOTA_BREACH, NotificationTrigger.PAYMENT_FAILED][i % 3],
    title: `Notification ${i + 1}`,
    message: `This is a sample notification message for item ${i + 1}`,
    recipient: i % 2 === 0 ? 'admin@company.com' : '#alerts',
    created_at: subDays(new Date(), Math.floor(i / 3)).toISOString(),
    sent_at: subDays(new Date(), Math.floor(i / 3)).toISOString(),
    delivered_at: i % 3 !== 1 ? subDays(new Date(), Math.floor(i / 3)).toISOString() : undefined,
    retry_count: i % 3 === 1 ? 2 : 0,
    max_retries: 3,
    error_message: i % 3 === 1 ? 'Connection timeout' : undefined
  }));

  const handleCreateChannel = async (data: CreateChannelRequest) => {
    try {
      await createChannel.mutateAsync(data);
      setShowChannelModal(false);
      refetchChannels();
    } catch (error) {
      console.error('Failed to create channel:', error);
    }
  };

  const handleEditChannel = (channel: NotificationChannel) => {
    setEditingChannel(channel);
    setShowChannelModal(true);
  };

  const handleDeleteChannel = async (channelId: string) => {
    if (window.confirm('Are you sure you want to delete this channel?')) {
      try {
        await deleteChannel.mutateAsync(channelId);
        refetchChannels();
      } catch (error) {
        console.error('Failed to delete channel:', error);
      }
    }
  };

  const handleTestChannel = async (channelId: string) => {
    try {
      await testChannel.mutateAsync({
        channel_id: channelId,
        message: 'This is a test notification from LCopilot monitoring system.'
      });
    } catch (error) {
      console.error('Failed to test channel:', error);
    }
  };

  const getTypeIcon = (type: NotificationType) => {
    switch (type) {
      case NotificationType.EMAIL: return <Mail className="h-4 w-4" />;
      case NotificationType.SLACK: return <MessageSquare className="h-4 w-4" />;
      case NotificationType.SMS: return <Smartphone className="h-4 w-4" />;
      case NotificationType.WEBHOOK: return <Webhook className="h-4 w-4" />;
      default: return <Bell className="h-4 w-4" />;
    }
  };

  if (channelsLoading || statsLoading) {
    return (
      <div className={className}>
        <div className="space-y-6">
          <Skeleton className="h-8 w-64" />
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-32" />
            ))}
          </div>
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className={className}>
      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Bell className="h-6 w-6" />
            Notifications Management
          </h1>
          <p className="text-muted-foreground">
            Configure notification channels and monitor delivery status
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            onClick={() => {
              setEditingChannel(null);
              setShowChannelModal(true);
            }}
            className="gap-2"
          >
            <Plus className="h-4 w-4" />
            Add Channel
          </Button>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Sent</CardTitle>
            <Send className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{mockStats.total_sent.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Last 7 days
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Delivery Rate</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{mockStats.delivery_rate}%</div>
            <div className="flex items-center space-x-1 mt-1">
              <TrendingUp className="h-3 w-3 text-green-600" />
              <span className="text-xs text-green-600">+2.1% vs last week</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Failed Notifications</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{mockStats.total_failed}</div>
            <p className="text-xs text-muted-foreground">
              Requires attention
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Avg Delivery Time</CardTitle>
            <Clock className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{mockStats.avg_delivery_time}s</div>
            <p className="text-xs text-muted-foreground">
              Average response time
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Main Content Tabs */}
      <Tabs value={activeTab} onValueChange={(value: any) => setActiveTab(value)}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="history">History</TabsTrigger>
          <TabsTrigger value="analytics">Analytics</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Notification Channels</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {mockChannels.map((channel) => (
                  <Card key={channel.id} className="relative">
                    <CardHeader className="pb-2">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          {getTypeIcon(channel.type)}
                          <CardTitle className="text-base">{channel.name}</CardTitle>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Badge variant={channel.enabled ? 'default' : 'secondary'}>
                            {channel.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <div>
                        <div className="text-sm font-medium">Triggers:</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {channel.triggers.map((trigger) => (
                            <Badge key={trigger} variant="outline" className="text-xs">
                              {formatNotificationTrigger(trigger)}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      <div>
                        <div className="text-sm font-medium">Priority Filter:</div>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {channel.priority_filter.map((priority) => (
                            <Badge
                              key={priority}
                              className={`text-xs ${getNotificationPriorityColor(priority)}`}
                            >
                              {priority}
                            </Badge>
                          ))}
                        </div>
                      </div>

                      {channel.recipients && channel.recipients.length > 0 && (
                        <div>
                          <div className="text-sm font-medium">Recipients:</div>
                          <div className="text-xs text-muted-foreground mt-1">
                            {channel.recipients.slice(0, 2).join(', ')}
                            {channel.recipients.length > 2 && ` +${channel.recipients.length - 2} more`}
                          </div>
                        </div>
                      )}

                      <div className="flex items-center space-x-2 pt-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleTestChannel(channel.id)}
                          disabled={testChannel.isPending}
                          className="gap-1"
                        >
                          <TestTube className="h-3 w-3" />
                          Test
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleEditChannel(channel)}
                          className="gap-1"
                        >
                          <Edit className="h-3 w-3" />
                          Edit
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDeleteChannel(channel.id)}
                          disabled={deleteChannel.isPending}
                          className="gap-1 text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-3 w-3" />
                          Delete
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Notification History</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {mockHistory.slice(0, 10).map((notification) => (
                  <div key={notification.id} className="flex items-center justify-between p-4 border rounded-lg">
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        {getTypeIcon(notification.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <Badge className={`text-xs ${getNotificationStatusColor(notification.status)}`}>
                            {notification.status}
                          </Badge>
                          <Badge className={`text-xs ${getNotificationPriorityColor(notification.priority)}`}>
                            {notification.priority}
                          </Badge>
                          <span className="text-xs text-muted-foreground">
                            {formatNotificationTrigger(notification.trigger)}
                          </span>
                        </div>
                        <div className="font-medium">{notification.title}</div>
                        <div className="text-sm text-muted-foreground truncate">
                          {notification.message}
                        </div>
                        <div className="text-xs text-muted-foreground mt-1">
                          To: {notification.recipient} • {format(new Date(notification.created_at), 'MMM dd, HH:mm')}
                        </div>
                        {notification.error_message && (
                          <div className="text-xs text-red-600 mt-1">
                            Error: {notification.error_message}
                          </div>
                        )}
                      </div>
                    </div>
                    {notification.retry_count > 0 && (
                      <div className="text-xs text-muted-foreground">
                        Retries: {notification.retry_count}/{notification.max_retries}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="analytics" className="space-y-4">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Delivery Trends</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={mockStats.recent_activity}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="timestamp" fontSize={12} tickLine={false} axisLine={false} />
                    <YAxis fontSize={12} tickLine={false} axisLine={false} />
                    <Tooltip />
                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#3b82f6"
                      strokeWidth={2}
                      dot={{ fill: '#3b82f6', r: 4 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Notifications by Type</CardTitle>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={Object.entries(mockStats.by_type).map(([type, count]) => ({
                        name: type,
                        value: count,
                        color: type === 'EMAIL' ? '#3b82f6' :
                               type === 'SLACK' ? '#8b5cf6' : '#f59e0b'
                      }))}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={100}
                      paddingAngle={5}
                      dataKey="value"
                    >
                      {Object.entries(mockStats.by_type).map((_, index) => (
                        <Cell
                          key={`cell-${index}`}
                          fill={['#3b82f6', '#8b5cf6', '#f59e0b'][index]}
                        />
                      ))}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Global Settings</CardTitle>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div>
                  <Label htmlFor="notifications-enabled">Enable Notifications</Label>
                  <p className="text-sm text-muted-foreground">
                    Master switch for all notification channels
                  </p>
                </div>
                <Switch id="notifications-enabled" defaultChecked />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <Label htmlFor="escalation-timeout">Escalation Timeout (minutes)</Label>
                  <Input
                    id="escalation-timeout"
                    type="number"
                    defaultValue="30"
                    className="mt-1"
                  />
                </div>
                <div>
                  <Label htmlFor="max-retries">Max Retries</Label>
                  <Input
                    id="max-retries"
                    type="number"
                    defaultValue="3"
                    className="mt-1"
                  />
                </div>
              </div>

              <div>
                <Label htmlFor="quiet-hours">Quiet Hours</Label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                  <div>
                    <Label htmlFor="quiet-start">Start Time</Label>
                    <Input
                      id="quiet-start"
                      type="time"
                      defaultValue="22:00"
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <Label htmlFor="quiet-end">End Time</Label>
                    <Input
                      id="quiet-end"
                      type="time"
                      defaultValue="08:00"
                      className="mt-1"
                    />
                  </div>
                  <div className="flex items-center space-x-2 mt-6">
                    <Switch id="quiet-enabled" />
                    <Label htmlFor="quiet-enabled">Enable</Label>
                  </div>
                </div>
              </div>

              <div className="pt-4">
                <Button>Save Settings</Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Channel Creation/Edit Modal */}
      <ChannelModal
        open={showChannelModal}
        onOpenChange={setShowChannelModal}
        channel={editingChannel}
        onSave={handleCreateChannel}
      />
    </div>
  );
}

// Channel Modal Component
interface ChannelModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  channel?: NotificationChannel | null;
  onSave: (data: CreateChannelRequest) => void;
}

function ChannelModal({ open, onOpenChange, channel, onSave }: ChannelModalProps) {
  const [formData, setFormData] = useState<CreateChannelRequest>({
    name: '',
    type: NotificationType.EMAIL,
    configuration: {},
    triggers: [],
    priority_filter: [],
    recipients: []
  });

  React.useEffect(() => {
    if (channel) {
      setFormData({
        name: channel.name,
        type: channel.type,
        configuration: channel.configuration,
        triggers: channel.triggers,
        priority_filter: channel.priority_filter,
        recipients: channel.recipients
      });
    } else {
      setFormData({
        name: '',
        type: NotificationType.EMAIL,
        configuration: {},
        triggers: [],
        priority_filter: [],
        recipients: []
      });
    }
  }, [channel]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave(formData);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {channel ? 'Edit Channel' : 'Create Notification Channel'}
          </DialogTitle>
          <DialogDescription>
            Configure a new notification channel for system alerts and updates.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <Label htmlFor="channel-name">Channel Name</Label>
              <Input
                id="channel-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Critical Alerts"
                required
              />
            </div>
            <div>
              <Label htmlFor="channel-type">Type</Label>
              <Select
                value={formData.type}
                onValueChange={(value: NotificationType) =>
                  setFormData(prev => ({ ...prev, type: value }))
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={NotificationType.EMAIL}>Email</SelectItem>
                  <SelectItem value={NotificationType.SLACK}>Slack</SelectItem>
                  <SelectItem value={NotificationType.SMS}>SMS</SelectItem>
                  <SelectItem value={NotificationType.WEBHOOK}>Webhook</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Type-specific configuration */}
          {formData.type === NotificationType.SLACK && (
            <div>
              <Label htmlFor="slack-webhook">Slack Webhook URL</Label>
              <Input
                id="slack-webhook"
                value={formData.configuration.webhook_url || ''}
                onChange={(e) => setFormData(prev => ({
                  ...prev,
                  configuration: { ...prev.configuration, webhook_url: e.target.value }
                }))}
                placeholder="https://hooks.slack.com/services/..."
                required
              />
            </div>
          )}

          {formData.type === NotificationType.EMAIL && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="from-email">From Email</Label>
                <Input
                  id="from-email"
                  value={formData.configuration.from_email || ''}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    configuration: { ...prev.configuration, from_email: e.target.value }
                  }))}
                  placeholder="noreply@company.com"
                  type="email"
                  required
                />
              </div>
              <div>
                <Label htmlFor="from-name">From Name</Label>
                <Input
                  id="from-name"
                  value={formData.configuration.from_name || ''}
                  onChange={(e) => setFormData(prev => ({
                    ...prev,
                    configuration: { ...prev.configuration, from_name: e.target.value }
                  }))}
                  placeholder="LCopilot System"
                />
              </div>
            </div>
          )}

          <div>
            <Label>Recipients</Label>
            <Textarea
              value={formData.recipients?.join('\n') || ''}
              onChange={(e) => setFormData(prev => ({
                ...prev,
                recipients: e.target.value.split('\n').filter(r => r.trim())
              }))}
              placeholder="Enter email addresses or phone numbers, one per line"
              rows={3}
            />
          </div>

          <div className="flex justify-end space-x-2 pt-4">
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit">
              {channel ? 'Update Channel' : 'Create Channel'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}