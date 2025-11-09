/**
 * Saved Views Manager Component
 * Provides UI for saving, loading, and managing filter presets
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
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
import {
  getSavedViews,
  saveView,
  updateView,
  deleteView,
  loadView,
  shareView,
  generateDeepLink,
  type SavedView,
} from "@/lib/savedViews";

interface SavedViewsManagerProps {
  dashboard: SavedView['dashboard'];
  section: string;
  currentFilters: Record<string, any>;
  onLoadView: (filters: Record<string, any>) => void;
  onSaveView?: (view: SavedView) => void;
}

export function SavedViewsManager({
  dashboard,
  section,
  currentFilters,
  onLoadView,
  onSaveView,
}: SavedViewsManagerProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [views, setViews] = React.useState<SavedView[]>([]);
  const [saveDialogOpen, setSaveDialogOpen] = React.useState(false);
  const [viewName, setViewName] = React.useState("");
  const [viewDescription, setViewDescription] = React.useState("");
  const [isShared, setIsShared] = React.useState(false);
  const [loading, setLoading] = React.useState(false);

  // Load views on mount
  React.useEffect(() => {
    const loaded = getSavedViews(dashboard, section);
    setViews(loaded);
  }, [dashboard, section]);

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

    setLoading(true);
    try {
      const newView = saveView({
        name: viewName.trim(),
        description: viewDescription.trim() || undefined,
        dashboard,
        section,
        filters: currentFilters,
        isShared,
        createdBy: user.id || 'anonymous',
      });

      setViews([...views, newView]);
      setSaveDialogOpen(false);
      setViewName("");
      setViewDescription("");
      setIsShared(false);

      toast({
        title: "View Saved",
        description: `Saved view "${newView.name}" has been created.`,
      });

      onSaveView?.(newView);
    } catch (error) {
      toast({
        title: "Save Failed",
        description: "Failed to save view. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleLoad = (view: SavedView) => {
    const loaded = loadView(view.id);
    if (loaded) {
      onLoadView(loaded.filters);
      toast({
        title: "View Loaded",
        description: `Loaded view "${loaded.name}".`,
      });
    }
  };

  const handleDelete = (viewId: string, viewName: string) => {
    if (confirm(`Delete saved view "${viewName}"?`)) {
      const deleted = deleteView(viewId);
      if (deleted) {
        setViews(views.filter((v) => v.id !== viewId));
        toast({
          title: "View Deleted",
          description: `Deleted view "${viewName}".`,
        });
      }
    }
  };

  const handleCopyLink = (view: SavedView) => {
    const link = generateDeepLink(view);
    navigator.clipboard.writeText(link);
    toast({
      title: "Link Copied",
      description: "Deep link copied to clipboard.",
    });
  };

  const handleShare = (view: SavedView) => {
    // For now, just toggle shared status
    // In future, this could open a dialog to select users/teams
    const updated = shareView(view.id, []);
    if (updated) {
      setViews(views.map((v) => (v.id === view.id ? updated : v)));
      toast({
        title: "View Shared",
        description: `View "${updated.name}" is now ${updated.isShared ? 'shared' : 'private'}.`,
      });
    }
  };

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
                        {view.isShared ? 'Unshare' : 'Share'}
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
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSaveDialogOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={loading || !viewName.trim()}>
              {loading && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save View
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

