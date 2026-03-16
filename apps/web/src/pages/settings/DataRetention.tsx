import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import {
  Download,
  Trash2,
  FileText,
  Clock,
  AlertCircle,
  Shield,
  ExternalLink,
} from "lucide-react";

const PRIVACY_EMAIL = "support@trdrhub.com";

function buildMailto(subject: string, body: string) {
  return `mailto:${PRIVACY_EMAIL}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
}

export function DataRetentionView({ embedded = false }: { embedded?: boolean }) {
  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="mb-2 text-3xl font-bold text-foreground">Data Retention & Privacy</h2>
          <p className="text-muted-foreground">
            Review privacy support options and request help from the TRDR Hub team.
          </p>
        </div>
      )}

      <Alert>
        <AlertCircle className="h-4 w-4" />
        <AlertTitle>Beta note</AlertTitle>
        <AlertDescription>
          Self-serve privacy request automation is not live in this beta yet. Download and deletion requests are currently handled through support so they do not appear as fake in-app records.
        </AlertDescription>
      </Alert>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Download className="h-4 w-4" />
              Data Download Request
            </CardTitle>
            <CardDescription>
              Request an export of the data currently associated with your account and company.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Use support when you need copies of profile data, validation history, uploaded document references, or billing history.</p>
            <Button asChild variant="outline" className="gap-2">
              <a
                href={buildMailto(
                  "TRDR Hub data download request",
                  "Please help me request a copy of my TRDR Hub account data.\n\nCompany:\nRequested scope:\nReason (optional):\n",
                )}
              >
                <Download className="h-4 w-4" />
                Email Privacy Support
              </a>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Trash2 className="h-4 w-4" />
              Data Deletion Request
            </CardTitle>
            <CardDescription>
              Request deletion or restricted handling of account data through support.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm text-muted-foreground">
            <p>Deletion and retention decisions may require manual review for legal, audit, and trade-finance recordkeeping reasons.</p>
            <Button asChild variant="destructive" className="gap-2">
              <a
                href={buildMailto(
                  "TRDR Hub data deletion request",
                  "Please help me request deletion or restricted handling of my TRDR Hub data.\n\nCompany:\nRequested scope:\nReason:\n",
                )}
              >
                <Trash2 className="h-4 w-4" />
                Email Deletion Request
              </a>
            </Button>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Shield className="h-4 w-4" />
              Your Privacy Rights
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>- request access to account-linked data</p>
            <p>- request correction of inaccurate profile details</p>
            <p>- request deletion where retention rules allow it</p>
            <p>- request export of selected records</p>
            <p>- request support clarification on retention obligations</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium">
              <Clock className="h-4 w-4" />
              Current Beta Process
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>- requests are handled through support, not an in-app workflow</p>
            <p>- download timing depends on account scope and manual review</p>
            <p>- deletion requests may require audit/compliance review first</p>
            <p>- you will receive follow-up by email once support picks up the request</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Request Tracking</CardTitle>
          <CardDescription>Current beta state for privacy request history</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <div className="rounded-lg border border-dashed border-border/70 bg-muted/30 p-4">
            TRDR Hub does not yet provide a live in-app tracker for privacy download or deletion requests. This page stays visible so the feature surface is honest, but request status is handled through support for now.
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant="outline">No fake request history</Badge>
            <Badge variant="outline">No fake download links</Badge>
            <Badge variant="outline">Support-assisted beta flow</Badge>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium">
            <FileText className="h-4 w-4" />
            Audit Visibility
          </CardTitle>
          <CardDescription>Where to look today for real account activity</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 text-sm text-muted-foreground">
          <p>For real beta activity, use your validation history, billing pages, and support conversations. Those surfaces reflect actual account activity better than a fake privacy tracker would.</p>
          <Button asChild variant="outline" className="gap-2">
            <a href="/lcopilot/support">
              <ExternalLink className="h-4 w-4" />
              Open Support
            </a>
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
