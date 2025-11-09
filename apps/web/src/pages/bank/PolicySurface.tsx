import * as React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Shield,
  FileText,
  Calendar,
  Globe,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";

// Mock data - replace with API calls
const mockActiveRulesets = [
  {
    domain: "icc",
    jurisdiction: "global",
    ruleset_version: "1.0.0",
    rulebook_version: "UCP600",
    effective_from: "2024-01-01T00:00:00Z",
    effective_to: null,
    rule_count: 39,
  },
  {
    domain: "icc",
    jurisdiction: "global",
    ruleset_version: "2.1.0",
    rulebook_version: "eUCP v2.1",
    effective_from: "2024-01-15T00:00:00Z",
    effective_to: null,
    rule_count: 14,
  },
];

const mockPolicyHistory = [
  {
    id: "policy-1",
    action: "published",
    ruleset_version: "1.0.0",
    rulebook_version: "UCP600",
    domain: "icc",
    jurisdiction: "global",
    published_by: "admin@example.com",
    published_at: "2024-01-01T00:00:00Z",
  },
  {
    id: "policy-2",
    action: "published",
    ruleset_version: "2.1.0",
    rulebook_version: "eUCP v2.1",
    domain: "icc",
    jurisdiction: "global",
    published_by: "admin@example.com",
    published_at: "2024-01-15T00:00:00Z",
  },
];

export function PolicySurface({ embedded = false }: { embedded?: boolean }) {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Policy Surface</h2>
          <p className="text-muted-foreground">View active rulesets and policy history for LC validation.</p>
        </div>
      </div>

      {/* Active Rulesets */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" /> Active Rulesets
          </CardTitle>
          <CardDescription>Currently active validation rulesets by domain and jurisdiction</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {mockActiveRulesets.map((ruleset, index) => (
              <div key={index} className="border rounded-lg p-4 space-y-3">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-lg">{ruleset.rulebook_version}</h3>
                      <Badge variant="outline">{ruleset.ruleset_version}</Badge>
                      <StatusBadge status="success">
                        <CheckCircle2 className="h-3 w-3 mr-1" /> Active
                      </StatusBadge>
                    </div>
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Globe className="h-4 w-4" />
                        {ruleset.domain.toUpperCase()} / {ruleset.jurisdiction}
                      </div>
                      <div className="flex items-center gap-1">
                        <FileText className="h-4 w-4" />
                        {ruleset.rule_count} rules
                      </div>
                      <div className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        Effective from {new Date(ruleset.effective_from).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                </div>
                {ruleset.effective_to && (
                  <div className="text-sm text-muted-foreground">
                    <AlertCircle className="h-4 w-4 inline mr-1" />
                    Scheduled to expire on {new Date(ruleset.effective_to).toLocaleDateString()}
                  </div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Policy History */}
      <Card>
        <CardHeader>
          <CardTitle>Policy History</CardTitle>
          <CardDescription>Recent ruleset publication and rollback events</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockPolicyHistory.map((event) => (
              <div key={event.id} className="flex items-center justify-between border-b pb-3 last:border-0">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <Badge variant={event.action === "published" ? "default" : "secondary"}>
                      {event.action}
                    </Badge>
                    <span className="font-medium">{event.rulebook_version}</span>
                    <Badge variant="outline">{event.ruleset_version}</Badge>
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {event.domain.toUpperCase()} / {event.jurisdiction} • Published by {event.published_by} • {new Date(event.published_at).toLocaleString()}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

