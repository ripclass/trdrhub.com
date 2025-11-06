import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { Settings as SettingsIcon } from 'lucide-react';

export function SystemSettings() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">System Settings</h2>
        <p className="text-muted-foreground">
          Configure global system preferences and defaults
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <SettingsIcon className="w-5 h-5" />
              General Settings
            </CardTitle>
            <CardDescription>Platform-wide configuration</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="platform-name">Platform Name</Label>
              <Input id="platform-name" defaultValue="LCopilot" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="support-email">Support Email</Label>
              <Input id="support-email" type="email" defaultValue="support@lcopilot.com" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="timezone">Default Timezone</Label>
              <Select defaultValue="utc">
                <SelectTrigger id="timezone">
                  <SelectValue placeholder="Select timezone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="utc">UTC</SelectItem>
                  <SelectItem value="est">Eastern (EST)</SelectItem>
                  <SelectItem value="pst">Pacific (PST)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-soft border-0">
          <CardHeader>
            <CardTitle>Security Settings</CardTitle>
            <CardDescription>Authentication and access controls</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Two-Factor Authentication</Label>
                <p className="text-sm text-muted-foreground">Require 2FA for all admin users</p>
              </div>
              <Switch defaultChecked />
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Session Timeout</Label>
                <p className="text-sm text-muted-foreground">Auto-logout after inactivity</p>
              </div>
              <Select defaultValue="30">
                <SelectTrigger className="w-24">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="15">15 min</SelectItem>
                  <SelectItem value="30">30 min</SelectItem>
                  <SelectItem value="60">1 hour</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>API Rate Limiting</Label>
                <p className="text-sm text-muted-foreground">Requests per minute</p>
              </div>
              <Input type="number" defaultValue="100" className="w-24" />
            </div>
          </CardContent>
        </Card>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle>Email & Notifications</CardTitle>
          <CardDescription>Configure system notification settings</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Alert Notifications</Label>
              <p className="text-sm text-muted-foreground">Send email for system alerts</p>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Weekly Reports</Label>
              <p className="text-sm text-muted-foreground">Send weekly usage reports</p>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>User Onboarding Emails</Label>
              <p className="text-sm text-muted-foreground">Automated welcome emails</p>
            </div>
            <Switch defaultChecked />
          </div>
        </CardContent>
      </Card>

      <div className="flex justify-end gap-3">
        <Button variant="outline">Reset to Defaults</Button>
        <Button>Save Changes</Button>
      </div>
    </>
  );
}

