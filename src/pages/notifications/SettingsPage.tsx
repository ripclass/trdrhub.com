import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Plus, Settings, Mail, MessageSquare, Webhook, Smartphone } from 'lucide-react';
import { ChannelSettings } from '@/components/notify/ChannelSettings';
import { TemplateEditor } from '@/components/notify/TemplateEditor';
import { SubscriptionEditor } from '@/components/notify/SubscriptionEditor';

interface NotificationChannel {
  id: string;
  name: string;
  channel_type: 'email' | 'slack' | 'webhook' | 'sms';
  active: boolean;
  default_recipient?: string;
  description?: string;
  created_at: string;
}

interface NotificationTemplate {
  id: string;
  template_key: string;
  locale: string;
  subject_template: string;
  body_template: string;
  active: boolean;
  description?: string;
}

interface NotificationSubscription {
  id: string;
  event_types: string[];
  channel_name: string;
  recipient?: string;
  digest_enabled: boolean;
  active: boolean;
  created_at: string;
}

const NotificationSettingsPage: React.FC = () => {
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [templates, setTemplates] = useState<NotificationTemplate[]>([]);
  const [subscriptions, setSubscriptions] = useState<NotificationSubscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [showChannelEditor, setShowChannelEditor] = useState(false);
  const [showTemplateEditor, setShowTemplateEditor] = useState(false);
  const [showSubscriptionEditor, setShowSubscriptionEditor] = useState(false);
  const [editingChannel, setEditingChannel] = useState<NotificationChannel | null>(null);
  const [editingTemplate, setEditingTemplate] = useState<NotificationTemplate | null>(null);
  const [editingSubscription, setEditingSubscription] = useState<NotificationSubscription | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Load channels
      const channelsResponse = await fetch('/api/notifications/channels');
      const channelsData = await channelsResponse.json();
      setChannels(channelsData);

      // Load templates
      const templatesResponse = await fetch('/api/notifications/templates');
      const templatesData = await templatesResponse.json();
      setTemplates(templatesData);

      // Load subscriptions
      const subscriptionsResponse = await fetch('/api/notifications/subscriptions');
      const subscriptionsData = await subscriptionsResponse.json();
      setSubscriptions(subscriptionsData);

    } catch (error) {
      console.error('Failed to load notification settings:', error);
    } finally {
      setLoading(false);
    }
  };

  const getChannelIcon = (type: string) => {
    switch (type) {
      case 'email':
        return <Mail className="h-4 w-4" />;
      case 'slack':
        return <MessageSquare className="h-4 w-4" />;
      case 'webhook':
        return <Webhook className="h-4 w-4" />;
      case 'sms':
        return <Smartphone className="h-4 w-4" />;
      default:
        return <Settings className="h-4 w-4" />;
    }
  };

  const getChannelTypeColor = (type: string) => {
    switch (type) {
      case 'email':
        return 'bg-blue-100 text-blue-800';
      case 'slack':
        return 'bg-purple-100 text-purple-800';
      case 'webhook':
        return 'bg-green-100 text-green-800';
      case 'sms':
        return 'bg-orange-100 text-orange-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const handleEditChannel = (channel: NotificationChannel) => {
    setEditingChannel(channel);
    setShowChannelEditor(true);
  };

  const handleEditTemplate = (template: NotificationTemplate) => {
    setEditingTemplate(template);
    setShowTemplateEditor(true);
  };

  const handleEditSubscription = (subscription: NotificationSubscription) => {
    setEditingSubscription(subscription);
    setShowSubscriptionEditor(true);
  };

  const handleSaveChannel = async (channelData: any) => {
    try {
      const method = editingChannel ? 'PUT' : 'POST';
      const url = editingChannel
        ? `/api/notifications/channels/${editingChannel.id}`
        : '/api/notifications/channels';

      const response = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(channelData)
      });

      if (response.ok) {
        await loadData();
        setShowChannelEditor(false);
        setEditingChannel(null);
      }
    } catch (error) {
      console.error('Failed to save channel:', error);
    }
  };

  const handleTestChannel = async (channelId: string) => {
    try {
      const response = await fetch(`/api/notifications/channels/${channelId}/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({})
      });

      const result = await response.json();

      if (result.status === 'success') {
        alert('Channel test successful!');
      } else {
        alert(`Channel test failed: ${result.message}`);
      }
    } catch (error) {
      console.error('Channel test failed:', error);
      alert('Channel test failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading notification settings...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-6 max-w-7xl">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Notification Settings</h1>
        <p className="text-gray-600 mt-1">
          Configure channels, templates, and subscriptions for notifications
        </p>
      </div>

      <Tabs defaultValue="channels" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="channels">Channels</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
          <TabsTrigger value="subscriptions">Subscriptions</TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Notification Channels</h2>
              <p className="text-sm text-gray-600">Configure email, Slack, SMS, and webhook channels</p>
            </div>
            <Button
              onClick={() => {
                setEditingChannel(null);
                setShowChannelEditor(true);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Channel
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {channels.map((channel) => (
              <Card key={channel.id} className="cursor-pointer hover:shadow-md transition-shadow">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      {getChannelIcon(channel.channel_type)}
                      <CardTitle className="text-lg">{channel.name}</CardTitle>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge className={getChannelTypeColor(channel.channel_type)}>
                        {channel.channel_type.toUpperCase()}
                      </Badge>
                      <Badge variant={channel.active ? 'default' : 'secondary'}>
                        {channel.active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                  </div>
                  {channel.description && (
                    <CardDescription>{channel.description}</CardDescription>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {channel.default_recipient && (
                      <div className="text-sm">
                        <span className="font-medium">Default recipient:</span>
                        <span className="ml-2 text-gray-600">{channel.default_recipient}</span>
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      Created: {new Date(channel.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex space-x-2 mt-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditChannel(channel)}
                    >
                      Edit
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestChannel(channel.id)}
                    >
                      Test
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {channels.length === 0 && (
            <Alert>
              <Settings className="h-4 w-4" />
              <AlertDescription>
                No notification channels configured. Add your first channel to start receiving notifications.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        <TabsContent value="templates" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Notification Templates</h2>
              <p className="text-sm text-gray-600">Customize message templates for different event types</p>
            </div>
            <Button
              onClick={() => {
                setEditingTemplate(null);
                setShowTemplateEditor(true);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Template
            </Button>
          </div>

          <div className="space-y-4">
            {templates.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{template.template_key}</CardTitle>
                      {template.description && (
                        <CardDescription>{template.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge variant="outline">{template.locale.toUpperCase()}</Badge>
                      <Badge variant={template.active ? 'default' : 'secondary'}>
                        {template.active ? 'Active' : 'Inactive'}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditTemplate(template)}
                      >
                        Edit
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <div>
                      <span className="font-medium text-sm">Subject:</span>
                      <p className="text-sm text-gray-600 mt-1">{template.subject_template}</p>
                    </div>
                    <div>
                      <span className="font-medium text-sm">Body (preview):</span>
                      <p className="text-sm text-gray-600 mt-1 line-clamp-3">
                        {template.body_template.length > 150
                          ? template.body_template.substring(0, 150) + '...'
                          : template.body_template
                        }
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {templates.length === 0 && (
            <Alert>
              <Settings className="h-4 w-4" />
              <AlertDescription>
                No notification templates configured. Add templates to customize notification messages.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>

        <TabsContent value="subscriptions" className="space-y-4">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-xl font-semibold">Notification Subscriptions</h2>
              <p className="text-sm text-gray-600">Manage event subscriptions and delivery preferences</p>
            </div>
            <Button
              onClick={() => {
                setEditingSubscription(null);
                setShowSubscriptionEditor(true);
              }}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Subscription
            </Button>
          </div>

          <div className="space-y-4">
            {subscriptions.map((subscription) => (
              <Card key={subscription.id}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{subscription.channel_name}</CardTitle>
                      <CardDescription>
                        {subscription.event_types.length === 0
                          ? 'All events'
                          : `${subscription.event_types.length} event types`
                        }
                      </CardDescription>
                    </div>
                    <div className="flex items-center space-x-2">
                      {subscription.digest_enabled && (
                        <Badge variant="outline">Digest</Badge>
                      )}
                      <Badge variant={subscription.active ? 'default' : 'secondary'}>
                        {subscription.active ? 'Active' : 'Inactive'}
                      </Badge>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => handleEditSubscription(subscription)}
                      >
                        Edit
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {subscription.recipient && (
                      <div className="text-sm">
                        <span className="font-medium">Recipient:</span>
                        <span className="ml-2 text-gray-600">{subscription.recipient}</span>
                      </div>
                    )}
                    {subscription.event_types.length > 0 && (
                      <div>
                        <span className="font-medium text-sm">Event types:</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {subscription.event_types.slice(0, 5).map((eventType) => (
                            <Badge key={eventType} variant="outline" className="text-xs">
                              {eventType}
                            </Badge>
                          ))}
                          {subscription.event_types.length > 5 && (
                            <Badge variant="outline" className="text-xs">
                              +{subscription.event_types.length - 5} more
                            </Badge>
                          )}
                        </div>
                      </div>
                    )}
                    <div className="text-xs text-gray-500">
                      Created: {new Date(subscription.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {subscriptions.length === 0 && (
            <Alert>
              <Settings className="h-4 w-4" />
              <AlertDescription>
                No notification subscriptions configured. Add subscriptions to receive notifications for specific events.
              </AlertDescription>
            </Alert>
          )}
        </TabsContent>
      </Tabs>

      {/* Modals */}
      {showChannelEditor && (
        <ChannelSettings
          channel={editingChannel}
          onSave={handleSaveChannel}
          onClose={() => {
            setShowChannelEditor(false);
            setEditingChannel(null);
          }}
        />
      )}

      {showTemplateEditor && (
        <TemplateEditor
          template={editingTemplate}
          onSave={async (templateData) => {
            try {
              const method = editingTemplate ? 'PUT' : 'POST';
              const url = editingTemplate
                ? `/api/notifications/templates/${editingTemplate.id}`
                : '/api/notifications/templates';

              const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(templateData)
              });

              if (response.ok) {
                await loadData();
                setShowTemplateEditor(false);
                setEditingTemplate(null);
              }
            } catch (error) {
              console.error('Failed to save template:', error);
            }
          }}
          onClose={() => {
            setShowTemplateEditor(false);
            setEditingTemplate(null);
          }}
        />
      )}

      {showSubscriptionEditor && (
        <SubscriptionEditor
          subscription={editingSubscription}
          channels={channels}
          onSave={async (subscriptionData) => {
            try {
              const method = editingSubscription ? 'PUT' : 'POST';
              const url = editingSubscription
                ? `/api/notifications/subscriptions/${editingSubscription.id}`
                : '/api/notifications/subscriptions';

              const response = await fetch(url, {
                method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscriptionData)
              });

              if (response.ok) {
                await loadData();
                setShowSubscriptionEditor(false);
                setEditingSubscription(null);
              }
            } catch (error) {
              console.error('Failed to save subscription:', error);
            }
          }}
          onClose={() => {
            setShowSubscriptionEditor(false);
            setEditingSubscription(null);
          }}
        />
      )}
    </div>
  );
};

export default NotificationSettingsPage;