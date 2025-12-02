/**
 * Hub Settings - Account & Workspace Settings
 * 
 * Manage account settings, API keys, and preferences.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell,
  Copy,
  Key,
  Lock,
  Moon,
  Palette,
  Plus,
  Save,
  Shield,
  Sun,
  Trash2,
  User,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used?: string;
  permissions: string[];
}

interface UserProfile {
  name: string;
  email: string;
  company: string;
  timezone: string;
  language: string;
}

interface NotificationSettings {
  email_usage_alerts: boolean;
  email_weekly_summary: boolean;
  email_new_features: boolean;
  email_security_alerts: boolean;
}

export default function HubSettings() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [activeTab, setActiveTab] = useState("profile");
  
  // Profile
  const [profile, setProfile] = useState<UserProfile>({
    name: "",
    email: "",
    company: "",
    timezone: "UTC",
    language: "en",
  });
  
  // Notifications
  const [notifications, setNotifications] = useState<NotificationSettings>({
    email_usage_alerts: true,
    email_weekly_summary: true,
    email_new_features: false,
    email_security_alerts: true,
  });
  
  // API Keys
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [newKeyDialogOpen, setNewKeyDialogOpen] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyValue, setNewKeyValue] = useState("");
  const [showNewKey, setShowNewKey] = useState(false);
  
  // Appearance
  const [theme, setTheme] = useState<"dark" | "light" | "system">("dark");
  
  // Delete account dialog
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

  useEffect(() => {
    // Load user settings
    setProfile({
      name: "User",
      email: "user@company.com",
      company: "My Company",
      timezone: "UTC",
      language: "en",
    });

    // Load API keys (mock)
    setApiKeys([]);
  }, []);

  const handleSaveProfile = async () => {
    setLoading(true);
    try {
      // POST to /api/settings/profile
      await new Promise((r) => setTimeout(r, 500));
      toast({
        title: "Settings Saved",
        description: "Your profile has been updated.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save settings",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveNotifications = async () => {
    setLoading(true);
    try {
      await new Promise((r) => setTimeout(r, 500));
      toast({
        title: "Notifications Updated",
        description: "Your notification preferences have been saved.",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save notification settings",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateApiKey = async () => {
    if (!newKeyName) return;

    setLoading(true);
    try {
      // POST to /api/settings/api-keys
      const mockKey = `trdr_live_${Math.random().toString(36).substring(2, 15)}${Math.random().toString(36).substring(2, 15)}`;
      
      setNewKeyValue(mockKey);
      setShowNewKey(true);
      
      setApiKeys([
        ...apiKeys,
        {
          id: Date.now().toString(),
          name: newKeyName,
          prefix: mockKey.substring(0, 12) + "...",
          created_at: new Date().toISOString(),
          permissions: ["read", "write"],
        },
      ]);

      toast({
        title: "API Key Created",
        description: "Make sure to copy your key - you won't see it again!",
      });
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to create API key",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteApiKey = async (key: ApiKey) => {
    setApiKeys(apiKeys.filter((k) => k.id !== key.id));
    toast({
      title: "API Key Deleted",
      description: `"${key.name}" has been revoked.`,
    });
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText(newKeyValue);
    toast({
      title: "Copied!",
      description: "API key copied to clipboard.",
    });
  };

  const handleCloseNewKeyDialog = () => {
    setNewKeyDialogOpen(false);
    setNewKeyName("");
    setNewKeyValue("");
    setShowNewKey(false);
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return (
    <div className="p-6 lg:p-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-slate-400">Manage your account and preferences</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="bg-slate-800/50 border border-white/5">
            <TabsTrigger value="profile" className="data-[state=active]:bg-slate-700">
              <User className="w-4 h-4 mr-2" />
              Profile
            </TabsTrigger>
            <TabsTrigger value="notifications" className="data-[state=active]:bg-slate-700">
              <Bell className="w-4 h-4 mr-2" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="api" className="data-[state=active]:bg-slate-700">
              <Key className="w-4 h-4 mr-2" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="security" className="data-[state=active]:bg-slate-700">
              <Shield className="w-4 h-4 mr-2" />
              Security
            </TabsTrigger>
          </TabsList>

          {/* Profile Tab */}
          <TabsContent value="profile">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-slate-900/50 border-white/5">
                <CardHeader>
                  <CardTitle className="text-white">Personal Information</CardTitle>
                  <CardDescription className="text-slate-400">
                    Update your personal details
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="name" className="text-slate-300">Full Name</Label>
                    <Input
                      id="name"
                      value={profile.name}
                      onChange={(e) => setProfile({ ...profile, name: e.target.value })}
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="email" className="text-slate-300">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      value={profile.email}
                      onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="company" className="text-slate-300">Company Name</Label>
                    <Input
                      id="company"
                      value={profile.company}
                      onChange={(e) => setProfile({ ...profile, company: e.target.value })}
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-white/5">
                <CardHeader>
                  <CardTitle className="text-white">Preferences</CardTitle>
                  <CardDescription className="text-slate-400">
                    Customize your experience
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-slate-300">Timezone</Label>
                    <Select
                      value={profile.timezone}
                      onValueChange={(v) => setProfile({ ...profile, timezone: v })}
                    >
                      <SelectTrigger className="bg-slate-800 border-white/10 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-white/10">
                        <SelectItem value="UTC">UTC</SelectItem>
                        <SelectItem value="America/New_York">Eastern Time</SelectItem>
                        <SelectItem value="America/Los_Angeles">Pacific Time</SelectItem>
                        <SelectItem value="Europe/London">London</SelectItem>
                        <SelectItem value="Asia/Singapore">Singapore</SelectItem>
                        <SelectItem value="Asia/Dubai">Dubai</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-slate-300">Language</Label>
                    <Select
                      value={profile.language}
                      onValueChange={(v) => setProfile({ ...profile, language: v })}
                    >
                      <SelectTrigger className="bg-slate-800 border-white/10 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-slate-900 border-white/10">
                        <SelectItem value="en">English</SelectItem>
                        <SelectItem value="es">Español</SelectItem>
                        <SelectItem value="fr">Français</SelectItem>
                        <SelectItem value="de">Deutsch</SelectItem>
                        <SelectItem value="zh">中文</SelectItem>
                        <SelectItem value="ar">العربية</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label className="text-slate-300">Theme</Label>
                    <div className="flex gap-2">
                      {[
                        { value: "dark", icon: Moon, label: "Dark" },
                        { value: "light", icon: Sun, label: "Light" },
                        { value: "system", icon: Palette, label: "System" },
                      ].map(({ value, icon: Icon, label }) => (
                        <Button
                          key={value}
                          variant={theme === value ? "default" : "outline"}
                          size="sm"
                          onClick={() => setTheme(value as typeof theme)}
                          className={
                            theme === value
                              ? "bg-blue-500/20 text-blue-400 border-blue-500/30"
                              : "border-white/10 text-slate-400"
                          }
                        >
                          <Icon className="w-4 h-4 mr-1" />
                          {label}
                        </Button>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="flex justify-end mt-6">
              <Button
                onClick={handleSaveProfile}
                disabled={loading}
                className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Changes
              </Button>
            </div>
          </TabsContent>

          {/* Notifications Tab */}
          <TabsContent value="notifications">
            <Card className="bg-slate-900/50 border-white/5">
              <CardHeader>
                <CardTitle className="text-white">Email Notifications</CardTitle>
                <CardDescription className="text-slate-400">
                  Choose what emails you want to receive
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">Usage Alerts</p>
                    <p className="text-sm text-slate-400">
                      Get notified when you're approaching usage limits
                    </p>
                  </div>
                  <Switch
                    checked={notifications.email_usage_alerts}
                    onCheckedChange={(v) =>
                      setNotifications({ ...notifications, email_usage_alerts: v })
                    }
                  />
                </div>

                <Separator className="bg-white/5" />

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">Weekly Summary</p>
                    <p className="text-sm text-slate-400">
                      Receive a weekly report of your activity
                    </p>
                  </div>
                  <Switch
                    checked={notifications.email_weekly_summary}
                    onCheckedChange={(v) =>
                      setNotifications({ ...notifications, email_weekly_summary: v })
                    }
                  />
                </div>

                <Separator className="bg-white/5" />

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">New Features</p>
                    <p className="text-sm text-slate-400">
                      Be the first to know about new tools and updates
                    </p>
                  </div>
                  <Switch
                    checked={notifications.email_new_features}
                    onCheckedChange={(v) =>
                      setNotifications({ ...notifications, email_new_features: v })
                    }
                  />
                </div>

                <Separator className="bg-white/5" />

                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-white">Security Alerts</p>
                    <p className="text-sm text-slate-400">
                      Important security notifications (recommended)
                    </p>
                  </div>
                  <Switch
                    checked={notifications.email_security_alerts}
                    onCheckedChange={(v) =>
                      setNotifications({ ...notifications, email_security_alerts: v })
                    }
                  />
                </div>
              </CardContent>
            </Card>

            <div className="flex justify-end mt-6">
              <Button
                onClick={handleSaveNotifications}
                disabled={loading}
                className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
              >
                <Save className="w-4 h-4 mr-2" />
                Save Preferences
              </Button>
            </div>
          </TabsContent>

          {/* API Keys Tab */}
          <TabsContent value="api">
            <Card className="bg-slate-900/50 border-white/5">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="text-white">API Keys</CardTitle>
                    <CardDescription className="text-slate-400">
                      Manage your API keys for programmatic access
                    </CardDescription>
                  </div>
                  <Button
                    onClick={() => setNewKeyDialogOpen(true)}
                    className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Create Key
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {apiKeys.length > 0 ? (
                  <div className="space-y-3">
                    {apiKeys.map((key) => (
                      <div
                        key={key.id}
                        className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-white/5"
                      >
                        <div className="flex items-center gap-4">
                          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                            <Key className="w-5 h-5 text-emerald-400" />
                          </div>
                          <div>
                            <p className="font-medium text-white">{key.name}</p>
                            <p className="text-sm text-slate-400 font-mono">
                              {key.prefix}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          <div className="text-right text-sm">
                            <p className="text-slate-400">
                              Created {formatDate(key.created_at)}
                            </p>
                            {key.last_used && (
                              <p className="text-slate-500">
                                Last used {formatDate(key.last_used)}
                              </p>
                            )}
                          </div>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                            onClick={() => handleDeleteApiKey(key)}
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-12">
                    <Key className="w-12 h-12 text-slate-600 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-white mb-2">No API Keys</h3>
                    <p className="text-slate-400 text-sm mb-4">
                      Create an API key to access TRDR Hub programmatically.
                    </p>
                    <Button
                      variant="outline"
                      onClick={() => setNewKeyDialogOpen(true)}
                      className="border-white/10 text-slate-300"
                    >
                      <Plus className="w-4 h-4 mr-2" />
                      Create Your First Key
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Security Tab */}
          <TabsContent value="security">
            <div className="space-y-6">
              <Card className="bg-slate-900/50 border-white/5">
                <CardHeader>
                  <CardTitle className="text-white">Password</CardTitle>
                  <CardDescription className="text-slate-400">
                    Change your account password
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <Label className="text-slate-300">Current Password</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-slate-300">New Password</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label className="text-slate-300">Confirm New Password</Label>
                    <Input
                      type="password"
                      placeholder="••••••••"
                      className="bg-slate-800 border-white/10 text-white"
                    />
                  </div>
                  <Button className="bg-slate-800 hover:bg-slate-700 text-white">
                    <Lock className="w-4 h-4 mr-2" />
                    Update Password
                  </Button>
                </CardContent>
              </Card>

              <Card className="bg-slate-900/50 border-white/5">
                <CardHeader>
                  <CardTitle className="text-white">Two-Factor Authentication</CardTitle>
                  <CardDescription className="text-slate-400">
                    Add an extra layer of security to your account
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-slate-800 flex items-center justify-center">
                        <Shield className="w-5 h-5 text-slate-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">2FA is disabled</p>
                        <p className="text-sm text-slate-400">
                          Protect your account with authenticator app
                        </p>
                      </div>
                    </div>
                    <Button variant="outline" className="border-white/10 text-slate-300">
                      Enable 2FA
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-red-500/5 border-red-500/20">
                <CardHeader>
                  <CardTitle className="text-red-400">Danger Zone</CardTitle>
                  <CardDescription className="text-slate-400">
                    Irreversible actions for your account
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-white">Delete Account</p>
                      <p className="text-sm text-slate-400">
                        Permanently delete your account and all data
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      className="border-red-500/30 text-red-400 hover:bg-red-500/10"
                      onClick={() => setDeleteDialogOpen(true)}
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Delete Account
                    </Button>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

      {/* Create API Key Dialog */}
      <Dialog open={newKeyDialogOpen} onOpenChange={handleCloseNewKeyDialog}>
        <DialogContent className="bg-slate-900 border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">
              {showNewKey ? "API Key Created" : "Create API Key"}
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              {showNewKey
                ? "Copy your API key now. You won't be able to see it again!"
                : "Give your API key a name to identify it later."}
            </DialogDescription>
          </DialogHeader>

          {showNewKey ? (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  <span className="text-emerald-400 font-medium">Key Created Successfully</span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 rounded bg-slate-800 text-slate-300 text-sm font-mono overflow-x-auto">
                    {newKeyValue}
                  </code>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={handleCopyKey}
                    className="border-white/10"
                  >
                    <Copy className="w-4 h-4" />
                  </Button>
                </div>
              </div>
              <p className="text-sm text-amber-400">
                ⚠️ Make sure to copy your key now. You won't be able to see it again!
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="keyName" className="text-slate-300">
                  Key Name
                </Label>
                <Input
                  id="keyName"
                  placeholder="e.g., Production API, Development"
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  className="bg-slate-800 border-white/10 text-white"
                />
              </div>
            </div>
          )}

          <DialogFooter>
            {showNewKey ? (
              <Button
                onClick={handleCloseNewKeyDialog}
                className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
              >
                Done
              </Button>
            ) : (
              <>
                <Button
                  variant="outline"
                  onClick={handleCloseNewKeyDialog}
                  className="border-white/10 text-slate-300"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateApiKey}
                  disabled={!newKeyName || loading}
                  className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
                >
                  Create Key
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Account Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent className="bg-slate-900 border-white/10">
          <AlertDialogHeader>
            <AlertDialogTitle className="text-white">Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="text-slate-400">
              This action cannot be undone. This will permanently delete your account and remove
              all data from our servers.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel className="border-white/10 text-slate-300">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction className="bg-red-500 hover:bg-red-600 text-white">
              Delete Account
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

