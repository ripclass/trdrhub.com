/**
 * Content Library Component for SME Dashboards
 * Reuse past descriptions, HS codes, ports, and other frequently used content
 */
import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Library,
  Search,
  Copy,
  Star,
  StarOff,
  Plus,
  Trash2,
  Package,
  MapPin,
  FileText,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface ContentItem {
  id: string;
  type: "description" | "hs_code" | "port" | "incoterms" | "currency";
  value: string;
  label?: string;
  usageCount: number;
  lastUsed?: string;
  isFavorite: boolean;
  tags?: string[];
}

interface ContentLibraryProps {
  embedded?: boolean;
  onSelect?: (item: ContentItem) => void;
}

const STORAGE_KEY = "lcopilot_content_library";

// Mock data - replace with API calls
const mockContent: ContentItem[] = [
  {
    id: "desc-1",
    type: "description",
    value: "100% Cotton T-Shirts, Made in Bangladesh, HS Code: 6109.10.00",
    label: "Cotton T-Shirts",
    usageCount: 15,
    lastUsed: "2024-01-15",
    isFavorite: true,
    tags: ["textiles", "apparel"],
  },
  {
    id: "hs-1",
    type: "hs_code",
    value: "6109.10.00",
    label: "Cotton T-Shirts",
    usageCount: 12,
    lastUsed: "2024-01-18",
    isFavorite: true,
    tags: ["textiles"],
  },
  {
    id: "port-1",
    type: "port",
    value: "Chittagong Port, Bangladesh",
    label: "Chittagong Port",
    usageCount: 25,
    lastUsed: "2024-01-20",
    isFavorite: true,
    tags: ["bangladesh"],
  },
  {
    id: "port-2",
    type: "port",
    value: "Port of Singapore",
    label: "Singapore Port",
    usageCount: 8,
    lastUsed: "2024-01-10",
    isFavorite: false,
    tags: ["singapore"],
  },
];

export function ContentLibrary({ embedded = false, onSelect }: ContentLibraryProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = React.useState<"all" | "descriptions" | "hs_codes" | "ports">("all");
  const [searchQuery, setSearchQuery] = React.useState("");
  const [content, setContent] = React.useState<ContentItem[]>(mockContent);
  const [showAddDialog, setShowAddDialog] = React.useState(false);
  
  // Add new content state
  const [newContentType, setNewContentType] = React.useState<ContentItem["type"]>("description");
  const [newContentValue, setNewContentValue] = React.useState("");
  const [newContentLabel, setNewContentLabel] = React.useState("");

  // Load content from localStorage
  React.useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const storedContent: ContentItem[] = JSON.parse(stored);
        setContent([...mockContent, ...storedContent]);
      }
    } catch (error) {
      console.error("Failed to load content library:", error);
    }
  }, []);

  const filteredContent = React.useMemo(() => {
    let filtered = content;

    // Filter by type
    if (activeTab !== "all") {
      const typeMap: Record<string, ContentItem["type"]> = {
        descriptions: "description",
        hs_codes: "hs_code",
        ports: "port",
      };
      filtered = filtered.filter((item) => item.type === typeMap[activeTab]);
    }

    // Filter by search query
    if (searchQuery.trim()) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (item) =>
          item.value.toLowerCase().includes(query) ||
          item.label?.toLowerCase().includes(query) ||
          item.tags?.some((tag) => tag.toLowerCase().includes(query))
      );
    }

    // Sort by favorite, then usage count
    return filtered.sort((a, b) => {
      if (a.isFavorite !== b.isFavorite) return a.isFavorite ? -1 : 1;
      return b.usageCount - a.usageCount;
    });
  }, [content, activeTab, searchQuery]);

  const handleAddContent = () => {
    if (!newContentValue.trim()) {
      toast({
        title: "Value Required",
        description: "Please provide a value for the content item.",
        variant: "destructive",
      });
      return;
    }

    const newItem: ContentItem = {
      id: `content-${Date.now()}`,
      type: newContentType,
      value: newContentValue.trim(),
      label: newContentLabel.trim() || undefined,
      usageCount: 0,
      isFavorite: false,
    };

    const updated = [...content, newItem];
    setContent(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((item) => !mockContent.find((m) => m.id === item.id))));

    setNewContentValue("");
    setNewContentLabel("");
    setShowAddDialog(false);

    toast({
      title: "Content Added",
      description: "New content item has been added to your library.",
    });
  };

  const handleToggleFavorite = (id: string) => {
    const updated = content.map((item) =>
      item.id === id ? { ...item, isFavorite: !item.isFavorite } : item
    );
    setContent(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((item) => !mockContent.find((m) => m.id === item.id))));
  };

  const handleDelete = (id: string) => {
    if (confirm("Delete this content item?")) {
      const updated = content.filter((item) => item.id !== id);
      setContent(updated);
      localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((item) => !mockContent.find((m) => m.id === item.id))));
      toast({
        title: "Content Deleted",
        description: "Content item has been removed from your library.",
      });
    }
  };

  const handleSelectItem = (item: ContentItem) => {
    // Increment usage count
    const updated = content.map((c) =>
      c.id === item.id
        ? { ...c, usageCount: c.usageCount + 1, lastUsed: new Date().toISOString().split('T')[0] }
        : c
    );
    setContent(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated.filter((item) => !mockContent.find((m) => m.id === item.id))));

    // Copy to clipboard
    navigator.clipboard.writeText(item.value);
    
    toast({
      title: "Content Selected",
      description: `${item.label || item.value} copied to clipboard.`,
    });

    onSelect?.(item);
  };

  const getTypeIcon = (type: ContentItem["type"]) => {
    switch (type) {
      case "description":
        return <FileText className="h-4 w-4" />;
      case "hs_code":
        return <Package className="h-4 w-4" />;
      case "port":
        return <MapPin className="h-4 w-4" />;
      default:
        return <FileText className="h-4 w-4" />;
    }
  };

  const getTypeLabel = (type: ContentItem["type"]) => {
    switch (type) {
      case "description":
        return "Description";
      case "hs_code":
        return "HS Code";
      case "port":
        return "Port";
      case "incoterms":
        return "Incoterms";
      case "currency":
        return "Currency";
      default:
        return type;
    }
  };

  return (
    <div className="flex flex-col gap-6">
      {!embedded && (
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Content Library</h2>
          <p className="text-muted-foreground">
            Reuse frequently used descriptions, HS codes, ports, and other content to speed up your workflow.
          </p>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Your Content Library</CardTitle>
              <CardDescription>
                {filteredContent.length} item{filteredContent.length !== 1 ? 's' : ''} available
              </CardDescription>
            </div>
            <Button onClick={() => setShowAddDialog(true)}>
              <Plus className="h-4 w-4 mr-2" />
              Add Content
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search content library..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          {/* Tabs */}
          <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)}>
            <TabsList>
              <TabsTrigger value="all">All</TabsTrigger>
              <TabsTrigger value="descriptions">Descriptions</TabsTrigger>
              <TabsTrigger value="hs_codes">HS Codes</TabsTrigger>
              <TabsTrigger value="ports">Ports</TabsTrigger>
            </TabsList>

            <TabsContent value={activeTab} className="mt-4">
              {filteredContent.length === 0 ? (
                <div className="text-center py-12">
                  <Library className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <p className="text-muted-foreground">No content found</p>
                  <p className="text-sm text-muted-foreground mt-2">
                    {searchQuery ? "Try a different search term" : "Add your first content item to get started"}
                  </p>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Type</TableHead>
                      <TableHead>Label</TableHead>
                      <TableHead>Value</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredContent.map((item) => (
                      <TableRow key={item.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {getTypeIcon(item.type)}
                            <span className="text-sm">{getTypeLabel(item.type)}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            {item.label || "-"}
                            {item.isFavorite && <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />}
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="max-w-md truncate" title={item.value}>
                            {item.value}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{item.usageCount} times</Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleSelectItem(item)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleToggleFavorite(item.id)}
                            >
                              {item.isFavorite ? (
                                <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                              ) : (
                                <StarOff className="h-4 w-4" />
                              )}
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDelete(item.id)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Add Content Dialog */}
      {showAddDialog && (
        <Card>
          <CardHeader>
            <CardTitle>Add Content to Library</CardTitle>
            <CardDescription>
              Save frequently used content for quick access.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="content-type">Content Type</Label>
              <Select value={newContentType} onValueChange={(value) => setNewContentType(value as ContentItem["type"])}>
                <SelectTrigger id="content-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="description">Description</SelectItem>
                  <SelectItem value="hs_code">HS Code</SelectItem>
                  <SelectItem value="port">Port</SelectItem>
                  <SelectItem value="incoterms">Incoterms</SelectItem>
                  <SelectItem value="currency">Currency</SelectItem>
                </SelectContent>
              </Select>
            </div>
            
            <div>
              <Label htmlFor="content-label">Label (Optional)</Label>
              <Input
                id="content-label"
                placeholder="e.g., Cotton T-Shirts"
                value={newContentLabel}
                onChange={(e) => setNewContentLabel(e.target.value)}
              />
            </div>
            
            <div>
              <Label htmlFor="content-value">Value *</Label>
              <Textarea
                id="content-value"
                placeholder="Enter the content value..."
                value={newContentValue}
                onChange={(e) => setNewContentValue(e.target.value)}
                rows={3}
              />
            </div>
            
            <div className="flex items-center gap-2">
              <Button onClick={handleAddContent} disabled={!newContentValue.trim()}>
                Add Content
              </Button>
              <Button variant="outline" onClick={() => setShowAddDialog(false)}>
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

