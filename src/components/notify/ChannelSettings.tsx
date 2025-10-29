import React, { useState, useEffect } from 'react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Eye, EyeOff, Mail, MessageSquare, Webhook, Smartphone } from 'lucide-react';

interface ChannelSettingsProps {
  channel?: any;
  onSave: (channelData: any) => void;
  onClose: () => void;
}

interface ChannelConfig {
  [key: string]: any;
}

const ChannelSettings: React.FC<ChannelSettingsProps> = ({ channel, onSave, onClose }) => {
  const [formData, setFormData] = useState({
    name: '',
    channel_type: 'email' as 'email' | 'slack' | 'webhook' | 'sms',
    description: '',
    default_recipient: '',
    active: true
  });

  const [config, setConfig] = useState<ChannelConfig>({});
  const [showSecrets, setShowSecrets] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (channel) {
      setFormData({
        name: channel.name || '',
        channel_type: channel.channel_type || 'email',
        description: channel.description || '',
        default_recipient: channel.default_recipient || '',
        active: channel.active !== false
      });
      setConfig(channel.config || {});
    }
  }, [channel]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await onSave({
        ...formData,
        config: config
      });
    } catch (error) {
      console.error('Failed to save channel:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConfigChange = (key: string, value: any) => {
    setConfig(prev => ({
      ...prev,
      [key]: value
    }));
  };

  const renderConfigFields = () => {
    switch (formData.channel_type) {
      case 'email':
        return (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="smtp_host">SMTP Host *</Label>
                <Input
                  id="smtp_host"
                  value={config.smtp_host || ''}
                  onChange={(e) => handleConfigChange('smtp_host', e.target.value)}
                  placeholder="smtp.gmail.com"
                  required
                />
              </div>
              <div>
                <Label htmlFor="smtp_port">SMTP Port *</Label>
                <Input
                  id="smtp_port"
                  type="number"
                  value={config.smtp_port || 587}
                  onChange={(e) => handleConfigChange('smtp_port', parseInt(e.target.value))}
                  placeholder="587"
                  required
                />
              </div>
            </div>
            <div>
              <Label htmlFor="from_email">From Email *</Label>
              <Input
                id="from_email"
                type="email"
                value={config.from_email || ''}
                onChange={(e) => handleConfigChange('from_email', e.target.value)}
                placeholder="noreply@company.com"
                required
              />
            </div>
            <div>
              <Label htmlFor="username">Username</Label>
              <Input
                id="username"
                value={config.username || ''}
                onChange={(e) => handleConfigChange('username', e.target.value)}
                placeholder="SMTP username"
              />
            </div>
            <div>
              <Label htmlFor="password">Password</Label>
              <div className="relative">
                <Input
                  id="password"
                  type={showSecrets ? 'text' : 'password'}
                  value={config.password || ''}
                  onChange={(e) => handleConfigChange('password', e.target.value)}
                  placeholder="SMTP password"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2"
                  onClick={() => setShowSecrets(!showSecrets)}
                >
                  {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <Switch
                id="use_tls"
                checked={config.use_tls !== false}
                onCheckedChange={(checked) => handleConfigChange('use_tls', checked)}
              />
              <Label htmlFor="use_tls">Use TLS</Label>
            </div>
          </div>
        );

      case 'slack':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="webhook_url">Slack Webhook URL *</Label>
              <div className="relative">
                <Input
                  id="webhook_url"
                  type={showSecrets ? 'text' : 'password'}
                  value={config.webhook_url || ''}
                  onChange={(e) => handleConfigChange('webhook_url', e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2"
                  onClick={() => setShowSecrets(!showSecrets)}
                >
                  {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Create a webhook URL in your Slack workspace settings
              </p>
            </div>
            <div>
              <Label htmlFor="channel">Default Channel</Label>
              <Input
                id="channel"
                value={config.channel || ''}
                onChange={(e) => handleConfigChange('channel', e.target.value)}
                placeholder="#notifications"
              />
            </div>
          </div>
        );

      case 'webhook':
        return (
          <div className="space-y-4">
            <div>
              <Label htmlFor="webhook_url">Webhook URL *</Label>
              <div className="relative">
                <Input
                  id="webhook_url"
                  type={showSecrets ? 'text' : 'password'}
                  value={config.webhook_url || ''}
                  onChange={(e) => handleConfigChange('webhook_url', e.target.value)}
                  placeholder="https://api.example.com/webhooks/notifications"
                  required
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2"
                  onClick={() => setShowSecrets(!showSecrets)}
                >
                  {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
            <div>
              <Label htmlFor="headers">Custom Headers (JSON)</Label>
              <Textarea
                id="headers"
                value={JSON.stringify(config.headers || {}, null, 2)}
                onChange={(e) => {
                  try {
                    const headers = JSON.parse(e.target.value);
                    handleConfigChange('headers', headers);
                  } catch {
                    // Invalid JSON, ignore
                  }
                }}
                placeholder={`{
  "Authorization": "Bearer token",
  "Content-Type": "application/json"
}`}
                rows={4}
              />
            </div>
          </div>
        );

      case 'sms':
        return (
          <div className="space-y-4">
            <Alert>
              <Smartphone className="h-4 w-4" />
              <AlertDescription>
                SMS notifications are currently in development. This is a placeholder configuration.
              </AlertDescription>
            </Alert>
            <div>
              <Label htmlFor="provider">SMS Provider</Label>
              <Select
                value={config.provider || 'twilio'}
                onValueChange={(value) => handleConfigChange('provider', value)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="twilio">Twilio</SelectItem>
                  <SelectItem value="aws_sns">AWS SNS</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label htmlFor="api_key">API Key</Label>
              <div className="relative">
                <Input
                  id="api_key"
                  type={showSecrets ? 'text' : 'password'}
                  value={config.api_key || ''}
                  onChange={(e) => handleConfigChange('api_key', e.target.value)}
                  placeholder="SMS provider API key"
                />
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  className="absolute right-2 top-1/2 transform -translate-y-1/2"
                  onClick={() => setShowSecrets(!showSecrets)}
                >
                  {showSecrets ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
              </div>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  const getChannelIcon = () => {
    switch (formData.channel_type) {
      case 'email':
        return <Mail className="h-5 w-5" />;
      case 'slack':
        return <MessageSquare className="h-5 w-5" />;
      case 'webhook':
        return <Webhook className="h-5 w-5" />;
      case 'sms':
        return <Smartphone className="h-5 w-5" />;
      default:
        return <Mail className="h-5 w-5" />;
    }
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center space-x-2">
            {getChannelIcon()}
            <span>{channel ? 'Edit Channel' : 'Add Channel'}</span>
          </DialogTitle>
          <DialogDescription>
            Configure notification channel settings and credentials
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Basic Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="name">Channel Name *</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="My Email Channel"
                  required
                />
              </div>

              <div>
                <Label htmlFor="channel_type">Channel Type *</Label>
                <Select
                  value={formData.channel_type}
                  onValueChange={(value: any) => {
                    setFormData({ ...formData, channel_type: value });
                    setConfig({}); // Reset config when type changes
                  }}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="email">Email (SMTP)</SelectItem>
                    <SelectItem value="slack">Slack Webhook</SelectItem>
                    <SelectItem value="webhook">Generic Webhook</SelectItem>
                    <SelectItem value="sms">SMS (Coming Soon)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="Channel description..."
                  rows={2}
                />
              </div>

              <div>
                <Label htmlFor="default_recipient">Default Recipient</Label>
                <Input
                  id="default_recipient"
                  value={formData.default_recipient}
                  onChange={(e) => setFormData({ ...formData, default_recipient: e.target.value })}
                  placeholder={
                    formData.channel_type === 'email' ? 'admin@company.com' :
                    formData.channel_type === 'slack' ? '#general' :
                    'Default recipient'
                  }
                />
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="active"
                  checked={formData.active}
                  onCheckedChange={(checked) => setFormData({ ...formData, active: checked })}
                />
                <Label htmlFor="active">Channel Active</Label>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Channel Configuration</CardTitle>
            </CardHeader>
            <CardContent>
              {renderConfigFields()}
            </CardContent>
          </Card>

          <div className="flex justify-end space-x-3 pt-4 border-t">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Channel'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
};

export { ChannelSettings };