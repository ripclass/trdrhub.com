import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { 
  Settings, 
  Bell, 
  Shield, 
  Palette,
  Globe,
  Key,
  Building,
  Save
} from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";

export default function SettingsPage() {
  const { toast } = useToast();
  
  const [settings, setSettings] = useState({
    // Thresholds
    warningThreshold: 15,
    failThreshold: 30,
    tbmlThreshold: 50,
    
    // Notifications
    emailAlerts: true,
    tbmlAlerts: true,
    weeklyDigest: false,
    
    // Preferences
    defaultCurrency: "USD",
    defaultUnit: "mt",
    autoVerify: true,
    
    // Company
    companyName: "",
    department: "",
  });

  const handleSave = () => {
    toast({
      title: "Settings Saved",
      description: "Your preferences have been updated.",
    });
  };

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Configure your price verification preferences.
        </p>
      </div>

      {/* Verification Thresholds */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Verification Thresholds
          </CardTitle>
          <CardDescription>
            Set the variance percentages that trigger warnings and failures.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid sm:grid-cols-3 gap-6">
            <div className="space-y-2">
              <Label htmlFor="warning">Warning Threshold (%)</Label>
              <Input
                id="warning"
                type="number"
                value={settings.warningThreshold}
                onChange={(e) => setSettings({ ...settings, warningThreshold: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">Variance above this triggers a warning</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="fail">Fail Threshold (%)</Label>
              <Input
                id="fail"
                type="number"
                value={settings.failThreshold}
                onChange={(e) => setSettings({ ...settings, failThreshold: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">Variance above this triggers a failure</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="tbml">TBML Flag Threshold (%)</Label>
              <Input
                id="tbml"
                type="number"
                value={settings.tbmlThreshold}
                onChange={(e) => setSettings({ ...settings, tbmlThreshold: parseInt(e.target.value) })}
              />
              <p className="text-xs text-muted-foreground">Variance above this flags potential TBML</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notifications
          </CardTitle>
          <CardDescription>
            Configure how you receive alerts and updates.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Email Alerts</p>
              <p className="text-sm text-muted-foreground">Receive email notifications for verifications</p>
            </div>
            <Switch
              checked={settings.emailAlerts}
              onCheckedChange={(checked) => setSettings({ ...settings, emailAlerts: checked })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">TBML Alerts</p>
              <p className="text-sm text-muted-foreground">Immediate alerts for TBML-flagged transactions</p>
            </div>
            <Switch
              checked={settings.tbmlAlerts}
              onCheckedChange={(checked) => setSettings({ ...settings, tbmlAlerts: checked })}
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Weekly Digest</p>
              <p className="text-sm text-muted-foreground">Summary email of all verifications</p>
            </div>
            <Switch
              checked={settings.weeklyDigest}
              onCheckedChange={(checked) => setSettings({ ...settings, weeklyDigest: checked })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Preferences */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Palette className="w-5 h-5" />
            Preferences
          </CardTitle>
          <CardDescription>
            Set your default options for verifications.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="grid sm:grid-cols-2 gap-6">
            <div className="space-y-2">
              <Label>Default Currency</Label>
              <Select
                value={settings.defaultCurrency}
                onValueChange={(value) => setSettings({ ...settings, defaultCurrency: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD - US Dollar</SelectItem>
                  <SelectItem value="EUR">EUR - Euro</SelectItem>
                  <SelectItem value="GBP">GBP - British Pound</SelectItem>
                  <SelectItem value="BDT">BDT - Bangladeshi Taka</SelectItem>
                  <SelectItem value="CNY">CNY - Chinese Yuan</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Default Unit</Label>
              <Select
                value={settings.defaultUnit}
                onValueChange={(value) => setSettings({ ...settings, defaultUnit: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mt">Metric Ton (MT)</SelectItem>
                  <SelectItem value="kg">Kilogram (kg)</SelectItem>
                  <SelectItem value="lb">Pound (lb)</SelectItem>
                  <SelectItem value="bbl">Barrel (bbl)</SelectItem>
                  <SelectItem value="oz">Ounce (oz)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">Auto-Verify on Upload</p>
              <p className="text-sm text-muted-foreground">Automatically verify prices when uploading documents</p>
            </div>
            <Switch
              checked={settings.autoVerify}
              onCheckedChange={(checked) => setSettings({ ...settings, autoVerify: checked })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Company Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Building className="w-5 h-5" />
            Company Information
          </CardTitle>
          <CardDescription>
            This information appears on generated reports.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="company">Company Name</Label>
              <Input
                id="company"
                value={settings.companyName}
                onChange={(e) => setSettings({ ...settings, companyName: e.target.value })}
                placeholder="Your Company Ltd."
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="department">Department</Label>
              <Input
                id="department"
                value={settings.department}
                onChange={(e) => setSettings({ ...settings, department: e.target.value })}
                placeholder="Trade Finance"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* API Access */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Key className="w-5 h-5" />
            API Access
          </CardTitle>
          <CardDescription>
            Integrate Price Verify with your systems.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between p-4 rounded-lg bg-muted/50">
            <div>
              <p className="font-medium">API Key</p>
              <p className="text-sm text-muted-foreground font-mono">pv_**********************</p>
            </div>
            <Badge>Professional Plan</Badge>
          </div>
          <p className="text-sm text-muted-foreground mt-4">
            API access is available on Professional and Business plans.{" "}
            <a href="#" className="text-primary hover:underline">Upgrade your plan</a>
          </p>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end">
        <Button onClick={handleSave}>
          <Save className="w-4 h-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}

