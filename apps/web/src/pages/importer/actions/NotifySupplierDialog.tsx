/**
 * Notify-supplier dialog.
 *
 * Takes a trigger element (usually the Notify button from SupplierDocActions),
 * opens a modal that collects { email, optional message }, fires the hook,
 * and surfaces success/failure via toast. No internal state beyond the form —
 * the hook owns isLoading/error.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useNotifySupplier } from "@/hooks/use-importer-actions";

export interface NotifySupplierDialogProps {
  sessionId: string;
  lcNumber?: string;
  trigger: React.ReactNode;
}

export function NotifySupplierDialog({
  sessionId,
  lcNumber,
  trigger,
}: NotifySupplierDialogProps) {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [open, setOpen] = useState(false);
  const notify = useNotifySupplier();
  const { toast } = useToast();

  const onSend = async () => {
    try {
      await notify.mutateAsync({
        validationSessionId: sessionId,
        supplierEmail: email,
        message: message || undefined,
        lcNumber,
      });
      toast({
        title: "Supplier notified",
        description: `Email sent to ${email}.`,
      });
      setOpen(false);
      setEmail("");
      setMessage("");
    } catch (err: any) {
      toast({
        title: "Failed to notify supplier",
        description: err?.message ?? "Please try again.",
        variant: "destructive",
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Notify Supplier</DialogTitle>
          <DialogDescription>
            Email the supplier the discrepancy details and the fix-pack
            reference so they can correct their documents.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <Label htmlFor="supplier-email">Supplier email</Label>
            <Input
              id="supplier-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="supplier@example.com"
            />
          </div>
          <div>
            <Label htmlFor="supplier-message">Message (optional)</Label>
            <Textarea
              id="supplier-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={4}
              placeholder="Add context — which shipment, deadline, etc."
            />
          </div>
        </div>
        <DialogFooter>
          <Button onClick={onSend} disabled={!email || notify.isLoading}>
            {notify.isLoading ? "Sending…" : "Send"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
