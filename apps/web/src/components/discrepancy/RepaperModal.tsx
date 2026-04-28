/**
 * RepaperModal — capture recipient + message, fire POST /repaper.
 *
 * On success, surfaces the recipient link (the access_token URL) so
 * the user can share it. Recipient lands on /repaper/{token} which
 * is the public-by-token page in pages/lcopilot/RepaperRecipient.tsx.
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Copy, Check } from "lucide-react";
import { requestRepaper } from "@/lib/lcopilot/discrepancyApi";

interface RepaperModalProps {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  discrepancyId: string;
  onCreated?: (recipientLink: string) => void;
}

export function RepaperModal({
  open,
  onOpenChange,
  discrepancyId,
  onCreated,
}: RepaperModalProps) {
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [link, setLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const reset = () => {
    setEmail("");
    setName("");
    setMessage("");
    setError(null);
    setLink(null);
    setCopied(false);
  };

  const handleClose = (next: boolean) => {
    if (!next) reset();
    onOpenChange(next);
  };

  const handleSubmit = async () => {
    if (!email.trim()) {
      setError("Recipient email is required");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const created = await requestRepaper(discrepancyId, {
        recipient_email: email.trim(),
        recipient_display_name: name.trim() || undefined,
        message: message.trim() || undefined,
      });
      const token = created.access_token;
      const recipientLink = token
        ? `${window.location.origin}/repaper/${token}`
        : "";
      setLink(recipientLink);
      onCreated?.(recipientLink);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })
        ?.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : (err as Error).message ?? "Failed to create request",
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopy = async () => {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore — user can copy manually from the input
    }
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Ask a counterparty to fix this</DialogTitle>
          <DialogDescription>
            They&rsquo;ll get a link to view the discrepancy and upload
            corrected documents. No account required.
          </DialogDescription>
        </DialogHeader>

        {!link && (
          <div className="space-y-3">
            <div className="space-y-1">
              <Label htmlFor="repaper-email">Recipient email</Label>
              <Input
                id="repaper-email"
                type="email"
                placeholder="supplier@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="repaper-name">Recipient name (optional)</Label>
              <Input
                id="repaper-name"
                type="text"
                placeholder="Name or company"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={submitting}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor="repaper-message">Message (optional)</Label>
              <textarea
                id="repaper-message"
                rows={4}
                placeholder="What needs to be fixed and any context to help them respond"
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                disabled={submitting}
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
              />
            </div>
            {error && <p className="text-sm text-rose-600">{error}</p>}
          </div>
        )}

        {link && (
          <div className="space-y-3">
            <p className="text-sm text-emerald-700">
              Request created. Share this link with the recipient:
            </p>
            <div className="flex items-center gap-2">
              <Input value={link} readOnly className="font-mono text-xs" />
              <Button
                size="sm"
                variant="outline"
                onClick={handleCopy}
                className="shrink-0"
              >
                {copied ? (
                  <>
                    <Check className="w-3.5 h-3.5 mr-1" /> Copied
                  </>
                ) : (
                  <>
                    <Copy className="w-3.5 h-3.5 mr-1" /> Copy
                  </>
                )}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              They can also reach the page by visiting the link directly.
              No login is required for the recipient.
            </p>
          </div>
        )}

        <DialogFooter>
          {!link && (
            <>
              <Button
                variant="ghost"
                onClick={() => handleClose(false)}
                disabled={submitting}
              >
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={submitting}>
                {submitting ? "Sending…" : "Send request"}
              </Button>
            </>
          )}
          {link && (
            <Button onClick={() => handleClose(false)}>Done</Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
