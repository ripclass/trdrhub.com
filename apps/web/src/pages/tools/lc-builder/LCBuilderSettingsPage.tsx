/**
 * LC Builder Settings Page
 */

import { useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Settings, Save, Building2, Globe, FileText } from "lucide-react";

export default function LCBuilderSettingsPage() {
  const { user } = useAuth();
  const { toast } = useToast();
  
  const [settings, setSettings] = useState({
    defaultCurrency: "USD",
    defaultPaymentTerms: "sight",
    defaultPresentationDays: "21",
    autoSaveEnabled: true,
    showRiskIndicators: true,
    defaultCountry: "",
    companyName: "",
    companyAddress: "",
    defaultBank: "",
    defaultSwift: "",
  });

  const handleSave = () => {
    // In production, this would save to API
    toast({
      title: "Settings Saved",
      description: "Your preferences have been updated",
    });
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Settings className="h-5 w-5 text-emerald-400" />
              Settings
            </h1>
            <p className="text-sm text-slate-400">
              Configure your LC Builder preferences
            </p>
          </div>
        </div>
      </div>

      <div className="px-6 py-6 space-y-6 max-w-3xl">
        {/* Default Values */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <FileText className="h-5 w-5 text-slate-400" />
              Default Values
            </CardTitle>
            <CardDescription>
              Pre-fill values for new LC applications
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Default Currency</Label>
                <Select
                  value={settings.defaultCurrency}
                  onValueChange={(v) => setSettings({ ...settings, defaultCurrency: v })}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD - US Dollar</SelectItem>
                    <SelectItem value="EUR">EUR - Euro</SelectItem>
                    <SelectItem value="GBP">GBP - British Pound</SelectItem>
                    <SelectItem value="CNY">CNY - Chinese Yuan</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              
              <div className="space-y-2">
                <Label>Default Payment Terms</Label>
                <Select
                  value={settings.defaultPaymentTerms}
                  onValueChange={(v) => setSettings({ ...settings, defaultPaymentTerms: v })}
                >
                  <SelectTrigger className="bg-slate-800 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="sight">At Sight</SelectItem>
                    <SelectItem value="usance">Usance</SelectItem>
                    <SelectItem value="deferred">Deferred Payment</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Default Presentation Period (Days)</Label>
              <Select
                value={settings.defaultPresentationDays}
                onValueChange={(v) => setSettings({ ...settings, defaultPresentationDays: v })}
              >
                <SelectTrigger className="bg-slate-800 border-slate-700 w-[200px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="7">7 Days</SelectItem>
                  <SelectItem value="14">14 Days</SelectItem>
                  <SelectItem value="21">21 Days (Default)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {/* Company Defaults */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Building2 className="h-5 w-5 text-slate-400" />
              Company Defaults
            </CardTitle>
            <CardDescription>
              Your company information for LC applications
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Company Name</Label>
              <Input
                value={settings.companyName}
                onChange={(e) => setSettings({ ...settings, companyName: e.target.value })}
                placeholder="Your Company Ltd"
                className="bg-slate-800 border-slate-700"
              />
            </div>
            
            <div className="space-y-2">
              <Label>Company Address</Label>
              <Input
                value={settings.companyAddress}
                onChange={(e) => setSettings({ ...settings, companyAddress: e.target.value })}
                placeholder="123 Business Street, City, Country"
                className="bg-slate-800 border-slate-700"
              />
            </div>
            
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2">
                <Label>Default Bank</Label>
                <Input
                  value={settings.defaultBank}
                  onChange={(e) => setSettings({ ...settings, defaultBank: e.target.value })}
                  placeholder="Standard Chartered Bank"
                  className="bg-slate-800 border-slate-700"
                />
              </div>
              
              <div className="space-y-2">
                <Label>Default SWIFT Code</Label>
                <Input
                  value={settings.defaultSwift}
                  onChange={(e) => setSettings({ ...settings, defaultSwift: e.target.value })}
                  placeholder="SCBLBDDX"
                  className="bg-slate-800 border-slate-700"
                />
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>Default Country</Label>
              <Input
                value={settings.defaultCountry}
                onChange={(e) => setSettings({ ...settings, defaultCountry: e.target.value })}
                placeholder="Bangladesh"
                className="bg-slate-800 border-slate-700"
              />
            </div>
          </CardContent>
        </Card>

        {/* Preferences */}
        <Card className="bg-slate-800/50 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Globe className="h-5 w-5 text-slate-400" />
              Preferences
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label>Auto-Save Drafts</Label>
                <p className="text-sm text-slate-400">
                  Automatically save your work while editing
                </p>
              </div>
              <Switch
                checked={settings.autoSaveEnabled}
                onCheckedChange={(v) => setSettings({ ...settings, autoSaveEnabled: v })}
              />
            </div>
            
            <div className="flex items-center justify-between">
              <div>
                <Label>Show Risk Indicators</Label>
                <p className="text-sm text-slate-400">
                  Display risk scores and warnings in the wizard
                </p>
              </div>
              <Switch
                checked={settings.showRiskIndicators}
                onCheckedChange={(v) => setSettings({ ...settings, showRiskIndicators: v })}
              />
            </div>
          </CardContent>
        </Card>

        {/* Save Button */}
        <Button
          className="w-full bg-emerald-600 hover:bg-emerald-700"
          onClick={handleSave}
        >
          <Save className="h-4 w-4 mr-2" />
          Save Settings
        </Button>
      </div>
    </div>
  );
}

