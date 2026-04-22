/**
 * Moment 2 action palette (Supplier Document Review results).
 *
 * Three actions, each backed by a Phase-3 endpoint:
 *   1. Generate Fix Pack       — downloads ZIP via signed S3 URL
 *   2. Notify Supplier         — opens NotifySupplierDialog
 *   3. Bank Precheck           — runs tightened verdict and toasts result
 */

import { Download, Send, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";
import {
  useSupplierFixPack,
  useBankPrecheck,
} from "@/hooks/use-importer-actions";
import { NotifySupplierDialog } from "./NotifySupplierDialog";

export interface SupplierDocActionsProps {
  sessionId: string;
  lcNumber?: string;
  bankName?: string;
}

export function SupplierDocActions({
  sessionId,
  lcNumber,
  bankName,
}: SupplierDocActionsProps) {
  const fixPack = useSupplierFixPack();
  const precheck = useBankPrecheck();
  const { toast } = useToast();

  const onFixPack = async () => {
    try {
      const result = await fixPack.mutateAsync({
        validationSessionId: sessionId,
        lcNumber,
      });
      // Open the signed URL in a new tab so the browser downloads it.
      window.open(result.download_url, "_blank", "noopener,noreferrer");
      toast({
        title: "Fix pack ready",
        description: `${result.file_name} (${result.issue_count} issue${result.issue_count === 1 ? "" : "s"})`,
      });
    } catch (err: any) {
      toast({
        title: "Fix pack generation failed",
        description: err?.message ?? "Please try again.",
        variant: "destructive",
      });
    }
  };

  const onPrecheck = async () => {
    try {
      const result = await precheck.mutateAsync({
        validationSessionId: sessionId,
        lcNumber: lcNumber ?? "",
        bankName,
      });
      const verdict = (result.precheck_verdict ?? "").toUpperCase();
      const c = result.counts;
      const counts = c
        ? `${c.critical} critical · ${c.major} major · ${c.minor} minor`
        : "";
      toast({
        title: verdict ? `Precheck: ${verdict}` : "Precheck complete",
        description: counts || result.message,
      });
    } catch (err: any) {
      toast({
        title: "Bank precheck failed",
        description: err?.message ?? "Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <div className="flex flex-col gap-2">
      <Button onClick={onFixPack} disabled={fixPack.isLoading} size="lg">
        <Download className="mr-2 h-4 w-4" />
        {fixPack.isLoading ? "Generating…" : "Generate Fix Pack"}
      </Button>
      <NotifySupplierDialog
        sessionId={sessionId}
        lcNumber={lcNumber}
        trigger={
          <Button variant="secondary">
            <Send className="mr-2 h-4 w-4" />
            Notify Supplier
          </Button>
        }
      />
      <Button
        variant="outline"
        onClick={onPrecheck}
        disabled={precheck.isLoading}
      >
        <ShieldCheck className="mr-2 h-4 w-4" />
        {precheck.isLoading ? "Prechecking…" : "Bank Precheck"}
      </Button>
    </div>
  );
}
