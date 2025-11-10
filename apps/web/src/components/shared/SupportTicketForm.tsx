import * as React from "react";
import { useState, useEffect } from "react";
import { useLocation } from "react-router-dom";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { api } from "@/api/client";
import { MessageCircle, Loader2 } from "lucide-react";

interface SupportContext {
  user_id?: string;
  user_email?: string;
  user_name?: string;
  user_role?: string;
  company_id?: string;
  current_page?: string;
  user_agent?: string;
  timestamp?: string;
}

interface SupportTicketFormProps {
  trigger?: React.ReactNode;
  defaultCategory?: string;
}

export function SupportTicketForm({ trigger, defaultCategory }: SupportTicketFormProps) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] = useState(true);
  const [context, setContext] = useState<SupportContext>({});
  const location = useLocation();
  const { toast } = useToast();

  const [formData, setFormData] = useState({
    subject: "",
    description: "",
    category: defaultCategory || "question",
    priority: "normal",
  });

  useEffect(() => {
    if (open) {
      // Fetch context when dialog opens
      setContextLoading(true);
      api.get<SupportContext>("/api/support/context")
        .then((response) => {
          setContext(response.data);
          setContextLoading(false);
        })
        .catch(() => {
          // Fallback context
          setContext({
            current_page: location.pathname,
            user_agent: navigator.userAgent,
            timestamp: new Date().toISOString(),
          });
          setContextLoading(false);
        });
    }
  }, [open, location.pathname]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const response = await api.post("/api/support/tickets", {
        ...formData,
        context: {
          ...context,
          current_page: location.pathname,
          user_agent: navigator.userAgent,
        },
      });

      toast({
        title: "Support Ticket Created",
        description: response.data.message || "Your ticket has been created successfully. We'll respond within 24 hours.",
      });

      // Reset form
      setFormData({
        subject: "",
        description: "",
        category: defaultCategory || "question",
        priority: "normal",
      });
      setOpen(false);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create support ticket. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const defaultTrigger = (
    <Button variant="outline" size="sm">
      <MessageCircle className="mr-2 h-4 w-4" />
      Create Support Ticket
    </Button>
  );

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        {trigger || defaultTrigger}
      </DialogTrigger>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Support Ticket</DialogTitle>
          <DialogDescription>
            Fill out the form below and we'll get back to you within 24 hours. Your current page and browser information will be automatically included.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="category">Category</Label>
            <Select
              value={formData.category}
              onValueChange={(value) => setFormData({ ...formData, category: value })}
            >
              <SelectTrigger id="category">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="bug">Bug Report</SelectItem>
                <SelectItem value="feature_request">Feature Request</SelectItem>
                <SelectItem value="question">Question</SelectItem>
                <SelectItem value="billing">Billing</SelectItem>
                <SelectItem value="technical">Technical Issue</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="priority">Priority</Label>
            <Select
              value={formData.priority}
              onValueChange={(value) => setFormData({ ...formData, priority: value })}
            >
              <SelectTrigger id="priority">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="low">Low</SelectItem>
                <SelectItem value="normal">Normal</SelectItem>
                <SelectItem value="high">High</SelectItem>
                <SelectItem value="urgent">Urgent</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="subject">Subject</Label>
            <Input
              id="subject"
              placeholder="Brief description of your issue"
              value={formData.subject}
              onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
              required
              maxLength={200}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Please provide as much detail as possible about your issue..."
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              required
              rows={6}
              maxLength={5000}
            />
            <p className="text-xs text-muted-foreground">
              {formData.description.length}/5000 characters
            </p>
          </div>

          {contextLoading ? (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading context information...</span>
            </div>
          ) : (
            <div className="text-xs text-muted-foreground bg-muted p-3 rounded-md">
              <p className="font-semibold mb-1">Context will be included:</p>
              <ul className="list-disc list-inside space-y-1">
                {context.current_page && <li>Current page: {context.current_page}</li>}
                {context.user_email && <li>Your email: {context.user_email}</li>}
                {context.user_role && <li>Your role: {context.user_role}</li>}
                <li>Browser information</li>
                <li>Timestamp</li>
              </ul>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={loading || contextLoading}>
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Submitting...
                </>
              ) : (
                "Submit Ticket"
              )}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}

