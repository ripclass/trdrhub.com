import * as React from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
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
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  FileText,
  Plus,
  Edit3,
  Trash2,
  Copy,
  RefreshCw,
  CheckCircle2,
  Save,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import { Badge } from "@/components/ui/badge";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";
import { smeTemplatesApi, type SMETemplate, type SMETemplateCreate, type SMETemplateUpdate } from "@/api/sme-templates";

// Use SMETemplate type from API
type Template = SMETemplate;

// Mock data - replace with API calls
const mockTemplates: Template[] = [
  {
    id: "template-1",
    name: "Standard LC Template",
    type: "lc",
    description: "Standard letter of credit template for regular trade",
    fields: {
      beneficiary: "{{company_name}}",
      amount: "USD {{amount}}",
      expiry_date: "{{expiry_days}} days from issue",
      shipment_terms: "FOB",
    },
    is_default: true,
    is_active: true,
    usage_count: 45,
    created_at: "2024-01-01T10:00:00Z",
    updated_at: "2024-01-15T14:30:00Z",
  },
  {
    id: "template-2",
    name: "Commercial Invoice Template",
    type: "document",
    document_type: "commercial_invoice",
    description: "Pre-filled commercial invoice with common fields",
    fields: {
      consignee: "{{default_consignee}}",
      shipper: "{{company_name}}",
      incoterms: "FOB",
      currency: "USD",
    },
    is_default: false,
    is_active: true,
    usage_count: 23,
    created_at: "2024-01-05T09:00:00Z",
    updated_at: "2024-01-10T11:20:00Z",
  },
];

export function TemplatesView({ embedded = false }: { embedded?: boolean }) {
  const { toast } = useToast();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = React.useState(false);
  const [templates, setTemplates] = React.useState<Template[]>([]);
  const [activeTab, setActiveTab] = React.useState<"lc" | "document">("lc");
  const [createDialogOpen, setCreateDialogOpen] = React.useState(false);
  const [editDialogOpen, setEditDialogOpen] = React.useState(false);
  const [selectedTemplate, setSelectedTemplate] = React.useState<Template | null>(null);
  const [templateName, setTemplateName] = React.useState("");
  const [templateDescription, setTemplateDescription] = React.useState("");
  const [templateFields, setTemplateFields] = React.useState<Record<string, string>>({});
  const [documentType, setDocumentType] = React.useState<string>("commercial_invoice");

  React.useEffect(() => {
    loadTemplates();
  }, [activeTab]);

  const loadTemplates = async () => {
    try {
      setLoading(true);
      const response = await smeTemplatesApi.list({
        type: activeTab,
        active_only: true,
      });
      setTemplates(response.items);
    } catch (error: any) {
      console.error("Failed to load templates:", error);
      // Fallback to mock data
      setTemplates(mockTemplates.filter((t) => t.type === activeTab));
      toast({
        title: "Warning",
        description: "Failed to load templates. Using cached data.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTemplate = () => {
    setTemplateName("");
    setTemplateDescription("");
    setTemplateFields({});
    setSelectedTemplate(null);
    setCreateDialogOpen(true);
  };

  const handleEditTemplate = (template: Template) => {
    setSelectedTemplate(template);
    setTemplateName(template.name);
    setTemplateDescription(template.description || "");
    setTemplateFields(template.fields);
    setEditDialogOpen(true);
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      toast({
        title: "Name Required",
        description: "Please provide a template name.",
        variant: "destructive",
      });
      return;
    }

    if (!user?.company_id) {
      toast({
        title: "Error",
        description: "Company ID not found",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      if (selectedTemplate) {
        // Update existing template
        const updateData: SMETemplateUpdate = {
          name: templateName,
          description: templateDescription || undefined,
          fields: templateFields,
          is_default: templates.some((t) => t.is_default && t.id !== selectedTemplate.id) ? false : true,
        };
        const updated = await smeTemplatesApi.update(selectedTemplate.id, updateData);
        await loadTemplates();
        toast({
          title: "Template Updated",
          description: `Template "${templateName}" has been updated successfully.`,
        });
        setEditDialogOpen(false);
      } else {
        // Create new template
        const createData: SMETemplateCreate = {
          name: templateName,
          type: activeTab,
          document_type: activeTab === "document" ? (documentType as any) : undefined,
          description: templateDescription || undefined,
          fields: templateFields,
          is_default: false,
        };
        const created = await smeTemplatesApi.create({
          ...createData,
          company_id: user.company_id,
          user_id: user.id || "",
        });
        await loadTemplates();
        toast({
          title: "Template Created",
          description: `Template "${templateName}" has been created successfully.`,
        });
        setCreateDialogOpen(false);
      }
      setSelectedTemplate(null);
      setTemplateName("");
      setTemplateDescription("");
      setTemplateFields({});
    } catch (error: any) {
      toast({
        title: "Save Failed",
        description: error.response?.data?.detail || "Failed to save template. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteTemplate = async (templateId: string) => {
    if (!confirm("Are you sure you want to delete this template?")) return;

    setLoading(true);
    try {
      await smeTemplatesApi.delete(templateId);
      await loadTemplates();
      toast({
        title: "Template Deleted",
        description: "Template has been deleted successfully.",
      });
    } catch (error: any) {
      toast({
        title: "Delete Failed",
        description: error.response?.data?.detail || "Failed to delete template. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleUseTemplate = async (template: Template) => {
    try {
      // Mark template as used
      await smeTemplatesApi.use(template.id);

      // Pre-fill template fields
      const prefilled = await smeTemplatesApi.prefill({
        template_id: template.id,
      });

      // Navigate to upload page with pre-filled data
      const prefilledData = encodeURIComponent(JSON.stringify(prefilled.fields));
      if (embedded) {
        navigate(`/lcopilot/${user?.role === "importer" ? "importer" : "exporter"}-dashboard?section=upload&template=${template.id}&prefill=${prefilledData}`);
      } else {
        navigate(`/${user?.role === "importer" ? "import" : "export"}-lc-upload?template=${template.id}&prefill=${prefilledData}`);
      }
      toast({
        title: "Template Applied",
        description: `Template "${template.name}" has been loaded with pre-filled data.`,
      });
    } catch (error: any) {
      toast({
        title: "Template Load Failed",
        description: error.response?.data?.detail || "Failed to load template. Please try again.",
        variant: "destructive",
      });
    }
  };

  const handleDuplicateTemplate = async (template: Template) => {
    setTemplateName(`${template.name} (Copy)`);
    setTemplateDescription(template.description || "");
    setTemplateFields(template.fields);
    setSelectedTemplate(null);
    setCreateDialogOpen(true);
  };

  const filteredTemplates = templates.filter((t) => t.type === activeTab);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Templates</h2>
          <p className="text-muted-foreground">
            Create and manage LC and document templates to speed up your validation workflow.
          </p>
        </div>
        <Button onClick={handleCreateTemplate} className="gap-2">
          <Plus className="h-4 w-4" />
          New Template
        </Button>
      </div>

      {/* Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium flex items-center gap-2">
            <FileText className="h-4 w-4" />
            About Templates
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Templates allow you to pre-fill common fields when creating new LC validations or uploading documents.
            Use variables like <code className="bg-muted px-1 rounded">{"{{company_name}}"}</code> or{" "}
            <code className="bg-muted px-1 rounded">{"{{default_consignee}}"}</code> to auto-populate from your company profile.
          </p>
          <p>
            <strong>LC Templates:</strong> Pre-fill LC-specific fields like beneficiary, amount, expiry dates, and shipment terms.
          </p>
          <p>
            <strong>Document Templates:</strong> Pre-fill document-specific fields like consignee, shipper, incoterms, and currency.
          </p>
        </CardContent>
      </Card>

      {/* Templates Tabs */}
      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as "lc" | "document")} className="w-full">
        <TabsList>
          <TabsTrigger value="lc">LC Templates ({templates.filter((t) => t.type === "lc").length})</TabsTrigger>
          <TabsTrigger value="document">
            Document Templates ({templates.filter((t) => t.type === "document").length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                {activeTab === "lc" ? "LC Templates" : "Document Templates"}
              </CardTitle>
              <CardDescription>
                {activeTab === "lc"
                  ? "Templates for letter of credit validations"
                  : "Templates for document uploads"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex items-center justify-center py-8 text-muted-foreground">
                  <RefreshCw className="h-5 w-5 animate-spin mr-2" /> Loading templates...
                </div>
              ) : filteredTemplates.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <FileText className="w-12 h-12 mx-auto mb-4 opacity-20" />
                  <p>No {activeTab === "lc" ? "LC" : "document"} templates yet</p>
                  <p className="text-sm">Create your first template to get started</p>
                  <Button onClick={handleCreateTemplate} className="mt-4" variant="outline">
                    <Plus className="h-4 w-4 mr-2" />
                    Create Template
                  </Button>
                </div>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Fields</TableHead>
                      <TableHead>Usage</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead className="text-right">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredTemplates.map((template) => (
                      <TableRow key={template.id}>
                        <TableCell className="font-medium">{template.name}</TableCell>
                        <TableCell>
                          <Badge variant="outline">
                            {template.type === "lc" ? "LC" : template.document_type?.replace(/_/g, " ") || "Document"}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {template.description || "-"}
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{Object.keys(template.fields).length} fields</Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          Used {template.usage_count} time{template.usage_count !== 1 ? "s" : ""}
                        </TableCell>
                        <TableCell>
                          {template.is_default ? (
                            <StatusBadge status="success">Default</StatusBadge>
                          ) : (
                            <span className="text-sm text-muted-foreground">-</span>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-2">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleUseTemplate(template)}
                              className="gap-2"
                            >
                              <FileText className="h-4 w-4" />
                              Use
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDuplicateTemplate(template)}
                              className="gap-2"
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleEditTemplate(template)}
                              className="gap-2"
                            >
                              <Edit3 className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleDeleteTemplate(template.id)}
                              className="text-destructive hover:text-destructive"
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
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Template Dialog */}
      <Dialog open={createDialogOpen || editDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setCreateDialogOpen(false);
          setEditDialogOpen(false);
          setSelectedTemplate(null);
        }
      }}>
        <DialogContent className="sm:max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{selectedTemplate ? "Edit Template" : "Create Template"}</DialogTitle>
            <DialogDescription>
              {selectedTemplate
                ? "Update your template details and fields"
                : `Create a new ${activeTab === "lc" ? "LC" : "document"} template`}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Template Name</Label>
              <Input
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
                placeholder="e.g., Standard LC Template"
              />
            </div>

            {activeTab === "document" && (
              <div className="space-y-2">
                <Label>Document Type</Label>
                <Select value={documentType} onValueChange={setDocumentType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select document type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="commercial_invoice">Commercial Invoice</SelectItem>
                    <SelectItem value="bill_of_lading">Bill of Lading</SelectItem>
                    <SelectItem value="packing_list">Packing List</SelectItem>
                    <SelectItem value="certificate_of_origin">Certificate of Origin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            )}

            <div className="space-y-2">
              <Label>Description (Optional)</Label>
              <Textarea
                value={templateDescription}
                onChange={(e) => setTemplateDescription(e.target.value)}
                placeholder="Describe when to use this template..."
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>Template Fields</Label>
              <div className="space-y-2 border rounded-lg p-4">
                <p className="text-sm text-muted-foreground mb-3">
                  Define field values. Use variables like {"{{company_name}}"} or {"{{default_consignee}}"} for dynamic values.
                </p>
                {activeTab === "lc" ? (
                  <div className="grid gap-3">
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Beneficiary</Label>
                      <Input
                        placeholder="e.g., {{company_name}}"
                        defaultValue={templateFields.beneficiary || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, beneficiary: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Amount</Label>
                      <Input
                        placeholder="e.g., USD {{amount}}"
                        defaultValue={templateFields.amount || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, amount: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Expiry Date</Label>
                      <Input
                        placeholder="e.g., {{expiry_days}} days from issue"
                        defaultValue={templateFields.expiry_date || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, expiry_date: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Shipment Terms</Label>
                      <Input
                        placeholder="e.g., FOB"
                        defaultValue={templateFields.shipment_terms || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, shipment_terms: e.target.value })}
                      />
                    </div>
                  </div>
                ) : (
                  <div className="grid gap-3">
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Consignee</Label>
                      <Input
                        placeholder="e.g., {{default_consignee}}"
                        defaultValue={templateFields.consignee || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, consignee: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Shipper</Label>
                      <Input
                        placeholder="e.g., {{company_name}}"
                        defaultValue={templateFields.shipper || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, shipper: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Incoterms</Label>
                      <Input
                        placeholder="e.g., FOB"
                        defaultValue={templateFields.incoterms || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, incoterms: e.target.value })}
                      />
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <Label className="text-xs">Currency</Label>
                      <Input
                        placeholder="e.g., USD"
                        defaultValue={templateFields.currency || ""}
                        onChange={(e) => setTemplateFields({ ...templateFields, currency: e.target.value })}
                      />
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button
                variant="outline"
                onClick={() => {
                  setCreateDialogOpen(false);
                  setEditDialogOpen(false);
                  setSelectedTemplate(null);
                }}
              >
                Cancel
              </Button>
              <Button onClick={handleSaveTemplate} disabled={loading || !templateName.trim()}>
                {loading ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Saving...
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4 mr-2" />
                    {selectedTemplate ? "Update Template" : "Create Template"}
                  </>
                )}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

