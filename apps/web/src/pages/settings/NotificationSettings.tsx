/**
 * Notification preferences page — Phase A3.
 *
 * Per-type toggles for in-app + email. Reads + writes
 * /api/notifications/preferences. Self-routes inside RequireAuth in
 * App.tsx at /settings/notifications.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { ChevronLeft, Save } from "lucide-react";
import {
  getPreferences,
  updatePreferences,
  type NotificationPreferenceEntry,
  type NotificationPreferences,
} from "@/lib/lcopilot/notificationsApi";

interface TypeMeta {
  type: string;
  label: string;
  description: string;
}

const TYPE_LABELS: TypeMeta[] = [
  {
    type: "discrepancy_raised",
    label: "Discrepancy raised",
    description:
      "When validation flags a new discrepancy on one of your LCs.",
  },
  {
    type: "discrepancy_resolved",
    label: "Discrepancy resolved",
    description:
      "When a discrepancy on one of your LCs is marked resolved.",
  },
  {
    type: "repaper_request_received",
    label: "Re-papering request received",
    description:
      "When another platform user asks you to fix a flagged document.",
  },
  {
    type: "repaper_resolved",
    label: "Re-papering completed",
    description:
      "When a recipient uploads corrected docs and re-validation finishes.",
  },
  {
    type: "validation_complete",
    label: "Validation complete (clean run)",
    description:
      "When a validation finishes with no findings. Skipped automatically when discrepancies are raised — you only get one notification per run.",
  },
  {
    type: "bulk_job_complete",
    label: "Bulk job complete",
    description:
      "When a bulk validation job you started finishes (succeeded, partial, or failed).",
  },
  {
    type: "lifecycle_transition",
    label: "Lifecycle state changes",
    description:
      "Heartbeat as your LC moves through lifecycle states (e.g. docs_in_preparation → docs_presented). Off by default.",
  },
];

export default function NotificationSettings() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<number | null>(null);
  const [prefs, setPrefs] = useState<
    Record<string, NotificationPreferenceEntry>
  >({});

  const fetchPrefs = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res: NotificationPreferences = await getPreferences();
      setPrefs(res.preferences ?? {});
    } catch (err) {
      setError((err as Error).message ?? "Failed to load preferences");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchPrefs();
  }, [fetchPrefs]);

  const setField = (
    type: string,
    key: keyof NotificationPreferenceEntry,
    value: boolean,
  ) => {
    setPrefs((prev) => {
      const existing = prev[type] ?? { in_app: true, email: false };
      return {
        ...prev,
        [type]: { ...existing, [key]: value },
      };
    });
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const res = await updatePreferences(prefs);
      setPrefs(res.preferences ?? {});
      setSavedAt(Date.now());
    } catch (err) {
      setError((err as Error).message ?? "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const visibleTypes = useMemo(() => {
    // Show known types from TYPE_LABELS first, then any extras returned
    // by the backend that don't have a label here yet.
    const known = new Set(TYPE_LABELS.map((t) => t.type));
    const extras = Object.keys(prefs).filter((t) => !known.has(t));
    return [
      ...TYPE_LABELS,
      ...extras.map((type) => ({
        type,
        label: type.replace(/_/g, " "),
        description: "",
      })),
    ];
  }, [prefs]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-8 space-y-4">
      <div className="flex items-center gap-2">
        <Button asChild variant="ghost" size="sm">
          <Link to="/lcopilot">
            <ChevronLeft className="w-4 h-4 mr-1" />
            Back
          </Link>
        </Button>
        <h1 className="text-xl font-semibold">Notification settings</h1>
      </div>

      {loading && (
        <Card>
          <CardContent className="py-6 text-sm text-muted-foreground">
            Loading…
          </CardContent>
        </Card>
      )}

      {error && (
        <div className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-700">
          {error}
        </div>
      )}

      {!loading && (
        <Card>
          <CardContent className="divide-y">
            {visibleTypes.map((meta) => {
              const entry =
                prefs[meta.type] ?? { in_app: true, email: false };
              return (
                <div
                  key={meta.type}
                  className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto] gap-3 py-4 items-center"
                >
                  <div>
                    <p className="text-sm font-medium">{meta.label}</p>
                    {meta.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {meta.description}
                      </p>
                    )}
                  </div>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    In-app
                    <Switch
                      checked={!!entry.in_app}
                      onCheckedChange={(v) =>
                        setField(meta.type, "in_app", !!v)
                      }
                      disabled={saving}
                    />
                  </label>
                  <label className="flex items-center gap-2 text-xs text-muted-foreground">
                    Email
                    <Switch
                      checked={!!entry.email}
                      onCheckedChange={(v) =>
                        setField(meta.type, "email", !!v)
                      }
                      disabled={saving}
                    />
                  </label>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-end gap-3">
        {savedAt && (
          <span className="text-xs text-emerald-700">Saved.</span>
        )}
        <Button onClick={handleSave} disabled={saving || loading}>
          <Save className="w-4 h-4 mr-1" />
          {saving ? "Saving…" : "Save changes"}
        </Button>
      </div>
    </div>
  );
}
