import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { bankApi, NotificationPreferences } from "@/api/bank";
import { Bell, Mail, MessageSquare, AlertTriangle, Save, Loader2 } from "lucide-react";

interface NotificationPreferencesProps {}

export function NotificationPreferences({}: NotificationPreferencesProps) {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  
  const [preferences, setPreferences] = useState<NotificationPreferences>({
    email_enabled: true,
    sms_enabled: false,
    job_completion_enabled: true,
    high_discrepancy_enabled: true,
    high_discrepancy_threshold: 5,
  });

  // Fetch current preferences
  const { data, isLoading } = useQuery({
    queryKey: ['bank-notification-preferences'],
    queryFn: () => bankApi.getNotificationPreferences(),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
  });

  // Update local state when data loads
  useEffect(() => {
    if (data) {
      setPreferences(data);
    }
  }, [data]);

  // Update preferences mutation
  const updateMutation = useMutation({
    mutationFn: (prefs: Partial<NotificationPreferences>) =>
      bankApi.updateNotificationPreferences(prefs),
    onSuccess: (response) => {
      toast({
        title: "Preferences Updated",
        description: "Your notification preferences have been saved successfully.",
      });
      // Update cache
      queryClient.setQueryData(['bank-notification-preferences'], response.preferences);
      setPreferences(response.preferences);
    },
    onError: (error: any) => {
      toast({
        title: "Update Failed",
        description: error.message || "Failed to update notification preferences. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleToggle = (key: keyof NotificationPreferences, value: boolean) => {
    setPreferences((prev) => ({ ...prev, [key]: value }));
  };

  const handleThresholdChange = (value: string) => {
    const numValue = parseInt(value, 10);
    if (!isNaN(numValue) && numValue >= 1 && numValue <= 20) {
      setPreferences((prev) => ({ ...prev, high_discrepancy_threshold: numValue }));
    }
  };

  const handleSave = () => {
    updateMutation.mutate(preferences);
  };

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Notification Preferences</CardTitle>
          <CardDescription>Loading preferences...</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="w-5 h-5" />
            Notification Preferences
          </CardTitle>
          <CardDescription>
            Configure how and when you receive notifications about LC validations.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Email Notifications */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="email-enabled" className="flex items-center gap-2">
                  <Mail className="w-4 h-4" />
                  Email Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Receive notifications via email
                </p>
              </div>
              <Switch
                id="email-enabled"
                checked={preferences.email_enabled}
                onCheckedChange={(checked) => handleToggle("email_enabled", checked)}
              />
            </div>
          </div>

          {/* SMS Notifications */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="sms-enabled" className="flex items-center gap-2">
                  <MessageSquare className="w-4 h-4" />
                  SMS Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Receive notifications via SMS (coming soon)
                </p>
              </div>
              <Switch
                id="sms-enabled"
                checked={preferences.sms_enabled}
                onCheckedChange={(checked) => handleToggle("sms_enabled", checked)}
                disabled={true}
              />
            </div>
          </div>

          {/* Job Completion Notifications */}
          <div className="space-y-4 border-t pt-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label htmlFor="job-completion-enabled" className="flex items-center gap-2">
                  <CheckCircle className="w-4 h-4" />
                  Job Completion Notifications
                </Label>
                <p className="text-sm text-muted-foreground">
                  Get notified when LC validation jobs complete
                </p>
              </div>
              <Switch
                id="job-completion-enabled"
                checked={preferences.job_completion_enabled}
                onCheckedChange={(checked) => handleToggle("job_completion_enabled", checked)}
                disabled={!preferences.email_enabled && !preferences.sms_enabled}
              />
            </div>
          </div>

          {/* High Discrepancy Alerts */}
          <div className="space-y-4 border-t pt-4">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label htmlFor="high-discrepancy-enabled" className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4" />
                    High Discrepancy Alerts
                  </Label>
                  <p className="text-sm text-muted-foreground">
                    Get alerted when LCs have high discrepancy counts
                  </p>
                </div>
                <Switch
                  id="high-discrepancy-enabled"
                  checked={preferences.high_discrepancy_enabled}
                  onCheckedChange={(checked) => handleToggle("high_discrepancy_enabled", checked)}
                  disabled={!preferences.email_enabled && !preferences.sms_enabled}
                />
              </div>

              {preferences.high_discrepancy_enabled && (
                <div className="ml-8 space-y-2">
                  <Label htmlFor="discrepancy-threshold">
                    Alert Threshold (discrepancy count)
                  </Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="discrepancy-threshold"
                      type="number"
                      min={1}
                      max={20}
                      value={preferences.high_discrepancy_threshold}
                      onChange={(e) => handleThresholdChange(e.target.value)}
                      className="w-24"
                    />
                    <span className="text-sm text-muted-foreground">
                      Alert when discrepancy count ≥ this number
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Valid range: 1-20 discrepancies
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Save Button */}
          <div className="flex justify-end pt-4 border-t">
            <Button
              onClick={handleSave}
              disabled={updateMutation.isPending}
            >
              {updateMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4 mr-2" />
                  Save Preferences
                </>
              )}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-muted/50">
        <CardContent className="pt-6">
          <div className="space-y-2">
            <h4 className="font-medium">About Notifications</h4>
            <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
              <li>Job completion notifications are sent when any validation finishes</li>
              <li>High discrepancy alerts are sent when discrepancy count exceeds your threshold</li>
              <li>Notifications include LC details and links to view full results</li>
              <li>You can disable individual notification types while keeping others enabled</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

