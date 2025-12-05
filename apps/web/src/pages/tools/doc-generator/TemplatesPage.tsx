/**
 * Document Templates Page
 * 
 * Manage reusable document templates with company defaults
 */

import { useState, useEffect } from "react";
import {
  FileText,
  Plus,
  Edit,
  Trash2,
  Star,
  StarOff,
  Loader2,
  Search,
  MoreHorizontal,
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogFooter,
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
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Template {
  id: string;
  name: string;
  description: string | null;
  is_default: boolean;
  use_count: number;
  beneficiary_name: string | null;
  bank_name: string | null;
  default_port_of_loading: string | null;
  default_incoterms: string | null;
  created_at: string;
}

interface TemplateForm {
  name: string;
  description: string;
  beneficiary_name: string;
  beneficiary_address: string;
  bank_name: string;
  bank_account: string;
  bank_swift: string;
  default_port_of_loading: string;
  default_incoterms: string;
  default_country_of_origin: string;
  default_shipping_marks: string;
}

const emptyForm: TemplateForm = {
  name: "",
  description: "",
  beneficiary_name: "",
  beneficiary_address: "",
  bank_name: "",
  bank_account: "",
  bank_swift: "",
  default_port_of_loading: "",
  default_incoterms: "",
  default_country_of_origin: "",
  default_shipping_marks: "",
};

export function TemplatesPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [templates, setTemplates] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<TemplateForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const response = await fetch(`${API_BASE}/doc-generator/catalog/templates`, {
        headers: {
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
      });
      if (response.ok) {
        setTemplates(await response.json());
      }
    } catch (error) {
      console.error("Error fetching templates:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      toast({ title: "Error", description: "Template name is required", variant: "destructive" });
      return;
    }

    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId 
        ? `${API_BASE}/doc-generator/catalog/templates/${editingId}`
        : `${API_BASE}/doc-generator/catalog/templates`;

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify(form),
      });

      if (!response.ok) throw new Error("Failed to save");

      toast({ title: editingId ? "Updated" : "Created", description: "Template saved successfully" });
      setDialogOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      fetchTemplates();
    } catch (error) {
      toast({ title: "Error", description: "Failed to save template", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this template?")) return;
    
    try {
      await fetch(`${API_BASE}/doc-generator/catalog/templates/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      toast({ title: "Deleted", description: "Template removed" });
      fetchTemplates();
    } catch (error) {
      toast({ title: "Error", description: "Failed to delete", variant: "destructive" });
    }
  };

  const handleSetDefault = async (id: string) => {
    try {
      await fetch(`${API_BASE}/api/doc-generator/templates/${id}/set-default`, {
        method: "POST",
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      toast({ title: "Default Set", description: "Template is now the default" });
      fetchTemplates();
    } catch (error) {
      toast({ title: "Error", description: "Failed to set default", variant: "destructive" });
    }
  };

  const openEdit = (template: Template) => {
    setEditingId(template.id);
    setForm({
      name: template.name,
      description: template.description || "",
      beneficiary_name: template.beneficiary_name || "",
      beneficiary_address: "",
      bank_name: template.bank_name || "",
      bank_account: "",
      bank_swift: "",
      default_port_of_loading: template.default_port_of_loading || "",
      default_incoterms: template.default_incoterms || "",
      default_country_of_origin: "",
      default_shipping_marks: "",
    });
    setDialogOpen(true);
  };

  const filteredTemplates = templates.filter(t =>
    t.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Document Templates</h1>
          <p className="text-slate-400">Save and reuse common document settings</p>
        </div>
        <Button onClick={() => { setEditingId(null); setForm(emptyForm); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          New Template
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search templates..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 bg-slate-800 border-slate-700"
        />
      </div>

      {/* Templates Table */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div className="text-center p-12">
              <FileText className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No templates yet</h3>
              <p className="text-slate-400 mb-4">Create a template to speed up document creation</p>
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Create Template
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800">
                  <TableHead className="text-slate-400">Name</TableHead>
                  <TableHead className="text-slate-400">Beneficiary</TableHead>
                  <TableHead className="text-slate-400">Bank</TableHead>
                  <TableHead className="text-slate-400">Incoterms</TableHead>
                  <TableHead className="text-slate-400">Uses</TableHead>
                  <TableHead className="text-slate-400 w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTemplates.map((template) => (
                  <TableRow key={template.id} className="border-slate-800 hover:bg-slate-800/50">
                    <TableCell className="text-white font-medium">
                      <div className="flex items-center gap-2">
                        {template.name}
                        {template.is_default && (
                          <Badge variant="outline" className="text-yellow-500 border-yellow-500">
                            Default
                          </Badge>
                        )}
                      </div>
                      {template.description && (
                        <p className="text-xs text-slate-400 mt-1">{template.description}</p>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-300">{template.beneficiary_name || "-"}</TableCell>
                    <TableCell className="text-slate-300">{template.bank_name || "-"}</TableCell>
                    <TableCell className="text-slate-300">{template.default_incoterms || "-"}</TableCell>
                    <TableCell className="text-slate-300">{template.use_count}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(template)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleSetDefault(template.id)}>
                            {template.is_default ? (
                              <>
                                <StarOff className="w-4 h-4 mr-2" />
                                Remove Default
                              </>
                            ) : (
                              <>
                                <Star className="w-4 h-4 mr-2" />
                                Set as Default
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(template.id)}
                            className="text-red-500"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Template" : "Create Template"}</DialogTitle>
            <DialogDescription>
              Save common settings to speed up document creation
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Template Name *</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="My Export Template"
                />
              </div>
              <div className="space-y-2">
                <Label>Description</Label>
                <Input
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="For US buyers"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Beneficiary Name</Label>
              <Input
                value={form.beneficiary_name}
                onChange={(e) => setForm({ ...form, beneficiary_name: e.target.value })}
                placeholder="Your Company Ltd."
              />
            </div>

            <div className="space-y-2">
              <Label>Beneficiary Address</Label>
              <Textarea
                value={form.beneficiary_address}
                onChange={(e) => setForm({ ...form, beneficiary_address: e.target.value })}
                placeholder="123 Export Street, City, Country"
                rows={2}
              />
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Bank Name</Label>
                <Input
                  value={form.bank_name}
                  onChange={(e) => setForm({ ...form, bank_name: e.target.value })}
                  placeholder="International Bank"
                />
              </div>
              <div className="space-y-2">
                <Label>Account Number</Label>
                <Input
                  value={form.bank_account}
                  onChange={(e) => setForm({ ...form, bank_account: e.target.value })}
                  placeholder="1234567890"
                />
              </div>
              <div className="space-y-2">
                <Label>SWIFT Code</Label>
                <Input
                  value={form.bank_swift}
                  onChange={(e) => setForm({ ...form, bank_swift: e.target.value })}
                  placeholder="INTLBANK"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Default Port of Loading</Label>
                <Input
                  value={form.default_port_of_loading}
                  onChange={(e) => setForm({ ...form, default_port_of_loading: e.target.value })}
                  placeholder="Chittagong, Bangladesh"
                />
              </div>
              <div className="space-y-2">
                <Label>Default Incoterms</Label>
                <Input
                  value={form.default_incoterms}
                  onChange={(e) => setForm({ ...form, default_incoterms: e.target.value })}
                  placeholder="FOB"
                />
              </div>
              <div className="space-y-2">
                <Label>Country of Origin</Label>
                <Input
                  value={form.default_country_of_origin}
                  onChange={(e) => setForm({ ...form, default_country_of_origin: e.target.value })}
                  placeholder="Bangladesh"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Default Shipping Marks</Label>
              <Textarea
                value={form.default_shipping_marks}
                onChange={(e) => setForm({ ...form, default_shipping_marks: e.target.value })}
                placeholder="N/M or your standard marks"
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editingId ? "Update" : "Create"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default TemplatesPage;

