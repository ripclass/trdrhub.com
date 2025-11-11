/**
 * Saved Views Manager Component
 * Provides UI for saving, loading, and managing filter presets
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useBankAuth } from "@/lib/bank/auth";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Bookmark,
  BookmarkCheck,
  Share2,
  Copy,
  Trash2,
  MoreVertical,
  Loader2,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { bankSavedViewsApi, type SavedView } from "@/api/bank";
import { generateDeepLink } from "@/lib/savedViews";

interface SavedViewsManagerProps {
  resource: 'results' | 'jobs';
  currentFilters: Record<string, any>;
  onLoadView: (filters: Record<string, any>) => void;
  onSaveView?: (view: SavedView) => void;
}

export function SavedViewsManager({
  resource,
  currentFilters,
  onLoadView,
  onSaveView,
}: SavedViewsManagerProps) {
  const { toast } = useToast();
  const { user } = useBankAuth();
  const queryClient = useQueryClient();
  const [saveDialogOpen, setSaveDialogOpen] = React.useState(false);
  const [viewName, setViewName] = React.useState("");
  const [viewDescription, setViewDescription] = React.useState("");
  const [isShared, setIsShared] = React.useState(false);
  const [isOrgDefault, setIsOrgDefault] = React.useState(false);

  // Fetch saved views from backend
  const { data: viewsData, isLoading: isLoadingViews } = useQuery({
    queryKey: ['bank-saved-views', resource],
    queryFn: () => bankSavedViewsApi.list(resource),
  });

  const views: SavedView[] = viewsData?.views || [];

  // Create view mutation
  const createMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; shared: boolean; is_org_default: boolean }) => {
      return bankSavedViewsApi.create({
        name: data.name,
        resource,
        query_params: currentFilters,
        columns: {}, // TODO: Add column preferences
        shared: data.shared,
        is_org_default: data.is_org_default,
      });
    },
    onSuccess: (newView) => {
      queryClient.invalidateQueries({ queryKey: ['bank-saved-views', resource] });
      setSaveDialogOpen(false);
      setViewName("");
      setViewDescription("");
      setIsShared(false);
      setIsOrgDefault(false);
      toast({
        title: "View Saved",
        description: `Saved view "${newView.name}" has been created.`,
      });
      onSaveView?.(newView);
    },
    onError: () => {
      toast({
        title: "Save Failed",
        description: "Failed to save view. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Update view mutation
  const updateMutation = useMutation({
    mutationFn: ({ viewId, updates }: { viewId: string; updates: Partial<SavedView> }) => {
      return bankSavedViewsApi.update(viewId, {
        name: updates.name,
        query_params: updates.query_params || currentFilters,
        shared: updates.shared,
        is_org_default: updates.is_org_default,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bank-saved-views', resource] });
      toast({
        title: "View Updated",
        description: "Saved view has been updated.",
      });
    },
    onError: () => {
      toast({
        title: "Update Failed",
        description: "Failed to update view. Please try again.",
        variant: "destructive",
      });
    },
  });

  // Delete view mutation
  const deleteMutation = useMutation({
    mutationFn: (viewId: string) => bankSavedViewsApi.delete(viewId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bank-saved-views', resource] });
      toast({
        title: "View Deleted",
        description: "Saved view has been deleted.",
      });
    },
    onError: () => {
      toast({
        title: "Delete Failed",
        description: "Failed to delete view. Please try again.",
        variant: "destructive",
      });
    },
  });

  const handleSave = () => {
    if (!viewName.trim()) {
      toast({
        title: "Name Required",
        description: "Please provide a name for this saved view.",
        variant: "destructive",
      });
      return;
    }

    if (!user) {
      toast({
        title: "Authentication Required",
        description: "Please sign in to save views.",
        variant: "destructive",
      });
      return;
    }

    createMutation.mutate({
      name: viewName.trim(),
      description: viewDescription.trim() || undefined,
      shared: isShared,
      is_org_default: isOrgDefault,
    });
  };

  const handleLoad = (view: SavedView) => {
    if (view.query_params) {
      onLoadView(view.query_params);
      toast({
        title: "View Loaded",
        description: `Loaded view "${view.name}".`,
      });
    }
  };

  const handleDelete = (viewId: string, viewName: string) => {
    if (confirm(`Delete saved view "${viewName}"?`)) {
      deleteMutation.mutate(viewId);
    }
  };

  const handleCopyLink = (view: SavedView) => {
    const link = generateDeepLink({
      id: view.id,
      name: view.name,
      dashboard: 'bank' as const,
      section: resource,
      filters: view.query_params || {},
      isShared: view.shared,
      createdBy: view.owner_id || '',
      createdAt: view.created_at,
      updatedAt: view.updated_at || view.created_at,
      usageCount: 0,
    });
    navigator.clipboard.writeText(link);
    toast({
      title: "Link Copied",
      description: "Deep link copied to clipboard.",
    });
  };

  const handleShare = (view: SavedView) => {
    updateMutation.mutate({
      viewId: view.id,
      updates: { shared: !view.shared },
    });
  };

  if (isLoadingViews) {
    return (
      <div className="flex items-center gap-2">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">Loading views...</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {/* Saved Views Dropdown */}
      {views.length > 0 && (
        <Select
          value=""
          onValueChange={(value) => {
            const view = views.find((v) => v.id === value);
            if (view) handleLoad(view);
          }}
        >
          <SelectTrigger className="w-[200px]">
            <SelectValue placeholder="Load Saved View" />
          </SelectTrigger>
          <SelectContent>
            {views.map((view) => (
              <SelectItem key={view.id} value={view.id}>
                <div className="flex items-center justify-between w-full">
                  <span>{view.name}</span>
                  {view.is_org_default && (
                    <Badge variant="secondary" className="ml-2 text-xs">Default</Badge>
                  )}
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        <MoreVertical className="h-3 w-3" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuLabel>Actions</DropdownMenuLabel>
                      <DropdownMenuItem onClick={() => handleLoad(view)}>
                        <BookmarkCheck className="h-4 w-4 mr-2" />
                        Load
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleCopyLink(view)}>
                        <Copy className="h-4 w-4 mr-2" />
                        Copy Link
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleShare(view)}>
                        <Share2 className="h-4 w-4 mr-2" />
                        {view.shared ? 'Unshare' : 'Share'}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => handleDelete(view.id, view.name)}
                        className="text-destructive"
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}

      {/* Save Current View Button */}
      <Dialog open={saveDialogOpen} onOpenChange={setSaveDialogOpen}>
        <DialogTrigger asChild>
          <Button variant="outline" size="sm">
            <Bookmark className="h-4 w-4 mr-2" />
            Save View
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Save Current View</DialogTitle>
            <DialogDescription>
              Save your current filters as a reusable view. You can share it with your team or keep it private.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div>
              <Label htmlFor="view-name">View Name *</Label>
              <Input
                id="view-name"
                value={viewName}
                onChange={(e) => setViewName(e.target.value)}
                placeholder="e.g., High Priority Discrepancies"
              />
            </div>
            <div>
              <Label htmlFor="view-description">Description (Optional)</Label>
              <Textarea
                id="view-description"
                value={viewDescription}
                onChange={(e) => setViewDescription(e.target.value)}
                placeholder="Describe what this view shows..."
                rows={3}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is-shared"
                  checked={isShared}
                  onChange={(e) => setIsShared(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="is-shared" className="cursor-pointer">
                  Share with team
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is-org-default"
                  checked={isOrgDefault}
                  onChange={(e) => setIsOrgDefault(e.target.checked)}
                  className="rounded"
                />
                <Label htmlFor="is-org-default" className="cursor-pointer">
                  Set as organization default
                </Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={createMutation.isPending || !viewName.trim()}>
              {createMutation.isPending && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save View
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

