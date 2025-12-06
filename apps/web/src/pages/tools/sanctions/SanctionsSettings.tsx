import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Settings,
  Bell,
  Shield,
  Globe,
  Mail,
  Zap,
  Database,
} from "lucide-react";

export default function SanctionsSettings() {
  return (
    <div className="p-6 space-y-6 max-w-4xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Settings className="w-6 h-6 text-red-400" />
          Settings
        </h1>
        <p className="text-slate-400 mt-1">
          Configure your sanctions screening preferences
        </p>
      </div>

      {/* Subscription */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-yellow-400" />
            Your Plan
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 bg-slate-800/50 rounded-lg border border-slate-700">
            <div>
              <h4 className="font-semibold text-white">Free Tier</h4>
              <p className="text-sm text-slate-400">10 screenings per month</p>
            </div>
            <div className="text-right">
              <p className="text-2xl font-bold text-white">7 / 10</p>
              <p className="text-sm text-slate-500">screenings remaining</p>
            </div>
          </div>
          <Button className="w-full bg-red-500 hover:bg-red-600 text-white">
            Upgrade to Professional - $99/mo
          </Button>
        </CardContent>
      </Card>

      {/* Default Lists */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Database className="w-5 h-5 text-red-400" />
            Default Screening Lists
          </CardTitle>
          <CardDescription className="text-slate-400">
            Select which lists to include in screenings by default
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            { code: "OFAC_SDN", name: "OFAC SDN", jurisdiction: "US", default: true },
            { code: "EU_CONS", name: "EU Consolidated", jurisdiction: "EU", default: true },
            { code: "UN_SC", name: "UN Security Council", jurisdiction: "UN", default: true },
            { code: "UK_OFSI", name: "UK OFSI", jurisdiction: "UK", default: true },
            { code: "BIS_EL", name: "BIS Entity List", jurisdiction: "US", default: false },
            { code: "OFAC_SSI", name: "OFAC Sectoral", jurisdiction: "US", default: false },
          ].map((list) => (
            <div
              key={list.code}
              className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700"
            >
              <div className="flex items-center gap-3">
                <Shield className="w-4 h-4 text-red-400" />
                <div>
                  <span className="text-white font-medium">{list.name}</span>
                  <Badge variant="outline" className="ml-2 border-slate-600 text-slate-400 text-xs">
                    {list.jurisdiction}
                  </Badge>
                </div>
              </div>
              <Switch defaultChecked={list.default} />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Notifications */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Bell className="w-5 h-5 text-red-400" />
            Notifications
          </CardTitle>
          <CardDescription className="text-slate-400">
            Manage how you receive alerts
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Mail className="w-4 h-4 text-slate-500" />
              <div>
                <Label className="text-white">Email Alerts</Label>
                <p className="text-sm text-slate-500">Receive alerts via email</p>
              </div>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Bell className="w-4 h-4 text-slate-500" />
              <div>
                <Label className="text-white">In-App Notifications</Label>
                <p className="text-sm text-slate-500">Show notifications in dashboard</p>
              </div>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="w-4 h-4 text-slate-500" />
              <div>
                <Label className="text-white">List Update Alerts</Label>
                <p className="text-sm text-slate-500">Alert when sanctions lists are updated</p>
              </div>
            </div>
            <Switch />
          </div>
        </CardContent>
      </Card>

      {/* Match Threshold */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <Globe className="w-5 h-5 text-red-400" />
            Matching Preferences
          </CardTitle>
          <CardDescription className="text-slate-400">
            Configure fuzzy matching sensitivity
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label className="text-white">Match Threshold</Label>
            <Select defaultValue="85">
              <SelectTrigger className="bg-slate-800 border-slate-700 text-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="bg-slate-800 border-slate-700">
                <SelectItem value="95" className="text-white">95% - Strict (fewer false positives)</SelectItem>
                <SelectItem value="85" className="text-white">85% - Balanced (recommended)</SelectItem>
                <SelectItem value="70" className="text-white">70% - Sensitive (more matches)</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-xs text-slate-500">
              Lower thresholds catch more potential matches but may include false positives
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Save */}
      <div className="flex justify-end">
        <Button className="bg-red-500 hover:bg-red-600 text-white">
          Save Settings
        </Button>
      </div>
    </div>
  );
}

