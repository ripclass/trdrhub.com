/**
 * Settings Page
 */
import { Settings, Globe, Bell, Download } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";

export default function HSCodeSettings() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <h1 className="text-xl font-bold flex items-center gap-2">
            <Settings className="h-5 w-5 text-emerald-400" />
            Settings
          </h1>
          <p className="text-sm text-slate-400">
            Configure your HS Code Finder preferences
          </p>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8 max-w-2xl space-y-6">
        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Default Settings
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-white">Default Import Country</Label>
                <p className="text-xs text-slate-500">Used when creating new classifications</p>
              </div>
              <Select defaultValue="US">
                <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="US">United States</SelectItem>
                  <SelectItem value="EU">European Union</SelectItem>
                  <SelectItem value="UK">United Kingdom</SelectItem>
                  <SelectItem value="CN">China</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-white">Currency</Label>
                <p className="text-xs text-slate-500">For duty calculations</p>
              </div>
              <Select defaultValue="USD">
                <SelectTrigger className="w-40 bg-slate-900 border-slate-700">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="USD">USD ($)</SelectItem>
                  <SelectItem value="EUR">EUR (€)</SelectItem>
                  <SelectItem value="GBP">GBP (£)</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-white">Tariff Updates</Label>
                <p className="text-xs text-slate-500">Get notified of rate changes</p>
              </div>
              <Switch />
            </div>
            <div className="flex items-center justify-between">
              <div>
                <Label className="text-white">FTA News</Label>
                <p className="text-xs text-slate-500">Trade agreement updates</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-slate-800 border-slate-700">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Download className="h-5 w-5" />
              Export Data
            </CardTitle>
            <CardDescription>Download your classification history</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full">
              <Download className="h-4 w-4 mr-2" />
              Export to CSV
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

