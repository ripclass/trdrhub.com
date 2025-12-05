/**
 * Settings Page
 * 
 * Tracking preferences and configuration.
 */

import { useState } from "react";
import {
  Settings,
  Bell,
  Mail,
  Smartphone,
  Globe,
  Clock,
  Save,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/components/ui/use-toast";

export default function SettingsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  const [isSaving, setIsSaving] = useState(false);
  
  // Settings state
  const [settings, setSettings] = useState({
    // Notification preferences
    emailNotifications: true,
    smsNotifications: false,
    pushNotifications: true,
    emailAddress: user?.email || "",
    phoneNumber: "",
    
    // Alert defaults
    defaultArrivalAlert: true,
    defaultDelayAlert: true,
    delayThresholdHours: 24,
    arrivalWindowHours: 48,
    
    // Display preferences
    timezone: "UTC",
    dateFormat: "DD/MM/YYYY",
    refreshInterval: 60,
    
    // Auto-tracking
    autoTrackFromLC: true,
    autoTrackFromInvoice: false,
  });

  const handleSave = async () => {
    setIsSaving(true);
    try {
      // In a real app, save to backend
      await new Promise(resolve => setTimeout(resolve, 500));
      toast({ title: "Saved", description: "Settings updated successfully" });
    } catch (error) {
      toast({ title: "Error", description: "Failed to save settings", variant: "destructive" });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Tracking Settings</h1>
          <p className="text-muted-foreground">Configure your tracking preferences</p>
        </div>
        <Button onClick={handleSave} disabled={isSaving}>
          {isSaving ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Save Changes
            </>
          )}
        </Button>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {/* Notification Preferences */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="w-5 h-5" />
              Notification Preferences
            </CardTitle>
            <CardDescription>Choose how you want to receive alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Mail className="w-4 h-4 text-muted-foreground" />
                  <div>
                    <p className="font-medium">Email Notifications</p>
                    <p className="text-xs text-muted-foreground">Receive alerts via email</p>
                  </div>
                </div>
                <Switch
                  checked={settings.emailNotifications}
                  onCheckedChange={(c) => setSettings({ ...settings, emailNotifications: c })}
                />
              </div>
              
              {settings.emailNotifications && (
                <div className="ml-6 space-y-2">
                  <Label>Email Address</Label>
                  <Input
                    type="email"
                    value={settings.emailAddress}
                    onChange={(e) => setSettings({ ...settings, emailAddress: e.target.value })}
                    placeholder="your@email.com"
                  />
                </div>
              )}

              <Separator />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Smartphone className="w-4 h-4 text-muted-foreground" />
                  <div>
                    <p className="font-medium">SMS Notifications</p>
                    <p className="text-xs text-muted-foreground">Receive alerts via SMS</p>
                  </div>
                </div>
                <Switch
                  checked={settings.smsNotifications}
                  onCheckedChange={(c) => setSettings({ ...settings, smsNotifications: c })}
                />
              </div>

              {settings.smsNotifications && (
                <div className="ml-6 space-y-2">
                  <Label>Phone Number</Label>
                  <Input
                    type="tel"
                    value={settings.phoneNumber}
                    onChange={(e) => setSettings({ ...settings, phoneNumber: e.target.value })}
                    placeholder="+1 234 567 8900"
                  />
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Alert Defaults */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Alert Defaults
            </CardTitle>
            <CardDescription>Default settings for new shipment alerts</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-create arrival alerts</p>
                <p className="text-xs text-muted-foreground">Alert me before shipment arrives</p>
              </div>
              <Switch
                checked={settings.defaultArrivalAlert}
                onCheckedChange={(c) => setSettings({ ...settings, defaultArrivalAlert: c })}
              />
            </div>

            {settings.defaultArrivalAlert && (
              <div className="space-y-2">
                <Label>Alert me (hours before arrival)</Label>
                <Select
                  value={settings.arrivalWindowHours.toString()}
                  onValueChange={(v) => setSettings({ ...settings, arrivalWindowHours: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="12">12 hours</SelectItem>
                    <SelectItem value="24">24 hours</SelectItem>
                    <SelectItem value="48">48 hours</SelectItem>
                    <SelectItem value="72">72 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-create delay alerts</p>
                <p className="text-xs text-muted-foreground">Alert me when shipment is delayed</p>
              </div>
              <Switch
                checked={settings.defaultDelayAlert}
                onCheckedChange={(c) => setSettings({ ...settings, defaultDelayAlert: c })}
              />
            </div>

            {settings.defaultDelayAlert && (
              <div className="space-y-2">
                <Label>Delay threshold (hours)</Label>
                <Select
                  value={settings.delayThresholdHours.toString()}
                  onValueChange={(v) => setSettings({ ...settings, delayThresholdHours: parseInt(v) })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="6">6 hours</SelectItem>
                    <SelectItem value="12">12 hours</SelectItem>
                    <SelectItem value="24">24 hours</SelectItem>
                    <SelectItem value="48">48 hours</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Display Preferences */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="w-5 h-5" />
              Display Preferences
            </CardTitle>
            <CardDescription>Customize how information is displayed</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Timezone</Label>
              <Select
                value={settings.timezone}
                onValueChange={(v) => setSettings({ ...settings, timezone: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="UTC">UTC</SelectItem>
                  <SelectItem value="Asia/Dhaka">Asia/Dhaka (GMT+6)</SelectItem>
                  <SelectItem value="Asia/Kolkata">Asia/Kolkata (GMT+5:30)</SelectItem>
                  <SelectItem value="Asia/Karachi">Asia/Karachi (GMT+5)</SelectItem>
                  <SelectItem value="Europe/London">Europe/London (GMT)</SelectItem>
                  <SelectItem value="America/New_York">America/New York (GMT-5)</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Date Format</Label>
              <Select
                value={settings.dateFormat}
                onValueChange={(v) => setSettings({ ...settings, dateFormat: v })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="DD/MM/YYYY">DD/MM/YYYY</SelectItem>
                  <SelectItem value="MM/DD/YYYY">MM/DD/YYYY</SelectItem>
                  <SelectItem value="YYYY-MM-DD">YYYY-MM-DD</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>Auto-refresh interval</Label>
              <Select
                value={settings.refreshInterval.toString()}
                onValueChange={(v) => setSettings({ ...settings, refreshInterval: parseInt(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="30">Every 30 seconds</SelectItem>
                  <SelectItem value="60">Every minute</SelectItem>
                  <SelectItem value="300">Every 5 minutes</SelectItem>
                  <SelectItem value="0">Manual only</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Integration Settings */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="w-5 h-5" />
              Integration Settings
            </CardTitle>
            <CardDescription>Automatic tracking from other tools</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-track from LC</p>
                <p className="text-xs text-muted-foreground">
                  Automatically track containers mentioned in validated LCs
                </p>
              </div>
              <Switch
                checked={settings.autoTrackFromLC}
                onCheckedChange={(c) => setSettings({ ...settings, autoTrackFromLC: c })}
              />
            </div>

            <Separator />

            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto-track from Invoices</p>
                <p className="text-xs text-muted-foreground">
                  Automatically track containers from uploaded invoices
                </p>
              </div>
              <Switch
                checked={settings.autoTrackFromInvoice}
                onCheckedChange={(c) => setSettings({ ...settings, autoTrackFromInvoice: c })}
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

