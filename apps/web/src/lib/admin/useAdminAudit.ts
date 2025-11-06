import * as React from "react";

import { useToast } from "@/components/ui/use-toast";
import { useAdminAuth } from "@/lib/admin/auth";

import { getAdminService } from "./services";
import type { AdminSection } from "./types";

const service = getAdminService();

interface AuditOptions {
  entityId?: string;
  metadata?: Record<string, unknown>;
}

export function useAdminAudit(section: AdminSection) {
  const { user } = useAdminAuth();
  const { toast } = useToast();

  return React.useCallback(
    async (action: string, options?: AuditOptions) => {
      try {
        await service.recordAdminAudit({
          action,
          section,
          actor: user?.email ?? "system",
          actorRole: user?.role ?? "viewer",
          entityId: options?.entityId,
          metadata: options?.metadata,
        });
      } catch (error) {
        toast({
          title: "Could not record audit trail",
          description: error instanceof Error ? error.message : "Unexpected error",
          variant: "destructive",
        });
      }
    },
    [section, toast, user?.email, user?.role],
  );
}

