import * as React from "react";
import { useToast } from "@/hooks/use-toast";
import { useBankAuth } from "@/lib/bank/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Building2, Plus, Edit, Trash2, X } from "lucide-react";
import { bankOrgsApi, type BankOrg, type BankOrgCreate } from "@/api/bank";
import { format } from "date-fns";

export function BankOrgsPage() {
  const { toast } = useToast();
  const { user } = useBankAuth();
  const isBankAdmin = user?.role === "bank_admin";
  
  // Early return if not admin
  if (!isBankAdmin) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Access Denied</CardTitle>
          <CardDescription>
            This section is restricted to bank administrators only.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            If you believe you should have access, please contact your bank administrator.
          </p>
        </CardContent>
      </Card>
    );
  }
  
  const [orgs, setOrgs] = React.useState<BankOrg[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [createOpen, setCreateOpen] = React.useState(false);
  const [editOrg, setEditOrg] = React.useState<BankOrg | null>(null);
  const [actionId, setActionId] = React.useState<string | null>(null);
  
  const [formData, setFormData] = React.useState<BankOrgCreate>({
    bank_company_id: user?.company_id || "",
    kind: "branch",
    name: "",
    code: "",
    level: 0,
    sort_order: 0,
    is_active: true,
  });

  const loadOrgs = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await bankOrgsApi.listOrgs();
      setOrgs(response.orgs);
    } catch (error) {
      console.error("Failed to load orgs", error);
      toast({
        title: "Error",
        description: "Failed to load organizations. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  React.useEffect(() => {
    loadOrgs();
  }, [loadOrgs]);

  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast({
        title: "Validation Error",
        description: "Organization name is required",
        variant: "destructive",
      });
      return;
    }

    setActionId("create");
    try {
      await bankOrgsApi.createOrg(formData);
      toast({
        title: "Success",
        description: "Organization created successfully",
      });
      setCreateOpen(false);
      setFormData({
        bank_company_id: user?.company_id || "",
        kind: "branch",
        name: "",
        code: "",
        level: 0,
        sort_order: 0,
        is_active: true,
      });
      loadOrgs();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to create organization",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleUpdate = async (orgId: string, updates: Partial<BankOrgCreate>) => {
    setActionId(orgId);
    try {
      await bankOrgsApi.updateOrg(orgId, updates);
      toast({
        title: "Success",
        description: "Organization updated successfully",
      });
      setEditOrg(null);
      loadOrgs();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update organization",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleDelete = async (orgId: string) => {
    if (!confirm("Are you sure you want to delete this organization? This action cannot be undone.")) {
      return;
    }

    setActionId(orgId);
    try {
      await bankOrgsApi.deleteOrg(orgId);
      toast({
        title: "Success",
        description: "Organization deleted successfully",
      });
      loadOrgs();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete organization",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleToggleActive = async (org: BankOrg) => {
    await handleUpdate(org.id, { is_active: !org.is_active });
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-semibold">Organizations</h2>
            <p className="text-sm text-muted-foreground">
              Manage bank branches, regions, and groups
            </p>
          </div>
        </div>
        <Card>
          <CardContent className="py-8">
            <div className="text-center text-muted-foreground">Loading...</div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Organizations</h2>
          <p className="text-sm text-muted-foreground">
            Manage bank branches, regions, and groups
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Create Organization
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Organization</DialogTitle>
              <DialogDescription>
                Add a new branch, region, or group to your bank
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="org-name">Name *</Label>
                <Input
                  id="org-name"
                  placeholder="e.g., New York Branch"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-code">Code</Label>
                <Input
                  id="org-code"
                  placeholder="e.g., NYC-001"
                  value={formData.code}
                  onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                />
                <p className="text-xs text-muted-foreground">
                  Short identifier (optional)
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-kind">Type *</Label>
                <Select
                  value={formData.kind}
                  onValueChange={(value: "group" | "region" | "branch") =>
                    setFormData({ ...formData, kind: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="branch">Branch</SelectItem>
                    <SelectItem value="region">Region</SelectItem>
                    <SelectItem value="group">Group</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="org-sort">Sort Order</Label>
                <Input
                  id="org-sort"
                  type="number"
                  min="0"
                  value={formData.sort_order}
                  onChange={(e) => setFormData({ ...formData, sort_order: parseInt(e.target.value) || 0 })}
                />
                <p className="text-xs text-muted-foreground">
                  Lower numbers appear first
                </p>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreate} disabled={actionId === "create"}>
                {actionId === "create" ? "Creating..." : "Create"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Organizations</CardTitle>
          <CardDescription>
            Manage organizational units for your bank
          </CardDescription>
        </CardHeader>
        <CardContent>
          {orgs.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground">
              <Building2 className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>No organizations found</p>
              <p className="text-sm mt-2">Create your first organization to get started</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Code</TableHead>
                  <TableHead>Type</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sort Order</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orgs.map((org) => (
                  <TableRow key={org.id}>
                    <TableCell className="font-medium">{org.name}</TableCell>
                    <TableCell>{org.code || "-"}</TableCell>
                    <TableCell>
                      <Badge variant="outline">{org.kind}</Badge>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Switch
                          checked={org.is_active ?? true}
                          onCheckedChange={() => handleToggleActive(org)}
                          disabled={actionId === org.id}
                        />
                        <span className="text-sm">
                          {org.is_active ?? true ? "Active" : "Inactive"}
                        </span>
                      </div>
                    </TableCell>
                    <TableCell>{org.sort_order}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex justify-end gap-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setEditOrg(org)}
                          disabled={actionId === org.id}
                        >
                          <Edit className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(org.id)}
                          disabled={actionId === org.id}
                        >
                          <Trash2 className="w-4 h-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      {editOrg && (
        <Dialog open={!!editOrg} onOpenChange={(open) => !open && setEditOrg(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Organization</DialogTitle>
              <DialogDescription>
                Update organization details
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="edit-name">Name *</Label>
                <Input
                  id="edit-name"
                  value={editOrg.name}
                  onChange={(e) => setEditOrg({ ...editOrg, name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-code">Code</Label>
                <Input
                  id="edit-code"
                  value={editOrg.code || ""}
                  onChange={(e) => setEditOrg({ ...editOrg, code: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="edit-sort">Sort Order</Label>
                <Input
                  id="edit-sort"
                  type="number"
                  min="0"
                  value={editOrg.sort_order}
                  onChange={(e) => setEditOrg({ ...editOrg, sort_order: parseInt(e.target.value) || 0 })}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditOrg(null)}>
                Cancel
              </Button>
              <Button
                onClick={() => {
                  if (editOrg) {
                    handleUpdate(editOrg.id, {
                      name: editOrg.name,
                      code: editOrg.code,
                      sort_order: editOrg.sort_order,
                    });
                  }
                }}
                disabled={actionId === editOrg.id}
              >
                {actionId === editOrg.id ? "Updating..." : "Update"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

