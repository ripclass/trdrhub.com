/**
 * Company Profile component for SME dashboards
 * Includes Compliance Info, Address Book, and Default Consignee/Shipper management
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
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Building2,
  MapPin,
  FileCheck,
  Plus,
  Edit,
  Trash2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Clock,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/status-badge";
import {
  companyProfileService,
  type CompanyAddress,
  type CompanyComplianceInfo,
  type DefaultConsigneeShipper,
  type CompanyAddressCreate,
  type CompanyComplianceInfoCreate,
  type DefaultConsigneeShipperCreate,
} from "@/lib/company-profile/service";

interface CompanyProfileViewProps {
  embedded?: boolean;
}

export function CompanyProfileView({ embedded = false }: CompanyProfileViewProps) {
  const { toast } = useToast();
  const { user } = useAuth();
  const [activeTab, setActiveTab] = React.useState<"compliance" | "addresses" | "consignee-shipper">("compliance");
  const [loading, setLoading] = React.useState(false);

  // Compliance state
  const [complianceInfo, setComplianceInfo] = React.useState<CompanyComplianceInfo | null>(null);
  const [complianceDialogOpen, setComplianceDialogOpen] = React.useState(false);

  // Addresses state
  const [addresses, setAddresses] = React.useState<CompanyAddress[]>([]);
  const [addressDialogOpen, setAddressDialogOpen] = React.useState(false);
  const [editingAddress, setEditingAddress] = React.useState<CompanyAddress | null>(null);

  // Consignee/Shipper state
  const [consigneeShipper, setConsigneeShipper] = React.useState<DefaultConsigneeShipper[]>([]);
  const [consigneeShipperDialogOpen, setConsigneeShipperDialogOpen] = React.useState(false);
  const [editingConsigneeShipper, setEditingConsigneeShipper] = React.useState<DefaultConsigneeShipper | null>(null);

  // Load data
  React.useEffect(() => {
    loadComplianceInfo();
    loadAddresses();
    loadConsigneeShipper();
  }, []);

  const loadComplianceInfo = async () => {
    try {
      setLoading(true);
      const data = await companyProfileService.getComplianceInfo();
      setComplianceInfo(data);
    } catch (error) {
      console.error("Failed to load compliance info:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadAddresses = async () => {
    try {
      setLoading(true);
      const data = await companyProfileService.listAddresses({ active_only: true });
      setAddresses(data.items);
    } catch (error) {
      console.error("Failed to load addresses:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadConsigneeShipper = async () => {
    try {
      setLoading(true);
      const data = await companyProfileService.listConsigneeShipper({ active_only: true });
      setConsigneeShipper(data.items);
    } catch (error) {
      console.error("Failed to load consignee/shipper:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSaveCompliance = async (data: CompanyComplianceInfoCreate) => {
    try {
      setLoading(true);
      if (!user?.company_id) {
        toast({
          title: "Error",
          description: "Company ID not found",
          variant: "destructive",
        });
        return;
      }

      await companyProfileService.upsertComplianceInfo({
        ...data,
        company_id: user.company_id,
      });
      await loadComplianceInfo();
      setComplianceDialogOpen(false);
      toast({
        title: "Success",
        description: "Compliance information saved successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save compliance information",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveAddress = async (data: CompanyAddressCreate) => {
    try {
      setLoading(true);
      if (!user?.company_id) {
        toast({
          title: "Error",
          description: "Company ID not found",
          variant: "destructive",
        });
        return;
      }

      if (editingAddress) {
        await companyProfileService.updateAddress(editingAddress.id, data);
      } else {
        await companyProfileService.createAddress({
          ...data,
          company_id: user.company_id,
        });
      }
      await loadAddresses();
      setAddressDialogOpen(false);
      setEditingAddress(null);
      toast({
        title: "Success",
        description: editingAddress ? "Address updated successfully" : "Address created successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save address",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteAddress = async (addressId: string) => {
    try {
      setLoading(true);
      await companyProfileService.deleteAddress(addressId);
      await loadAddresses();
      toast({
        title: "Success",
        description: "Address deleted successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete address",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSaveConsigneeShipper = async (data: DefaultConsigneeShipperCreate) => {
    try {
      setLoading(true);
      if (!user?.company_id) {
        toast({
          title: "Error",
          description: "Company ID not found",
          variant: "destructive",
        });
        return;
      }

      if (editingConsigneeShipper) {
        await companyProfileService.updateConsigneeShipper(editingConsigneeShipper.id, data);
      } else {
        await companyProfileService.createConsigneeShipper({
          ...data,
          company_id: user.company_id,
        });
      }
      await loadConsigneeShipper();
      setConsigneeShipperDialogOpen(false);
      setEditingConsigneeShipper(null);
      toast({
        title: "Success",
        description: editingConsigneeShipper ? "Consignee/Shipper updated successfully" : "Consignee/Shipper created successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to save consignee/shipper",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteConsigneeShipper = async (id: string) => {
    try {
      setLoading(true);
      await companyProfileService.deleteConsigneeShipper(id);
      await loadConsigneeShipper();
      toast({
        title: "Success",
        description: "Consignee/Shipper deleted successfully",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete consignee/shipper",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold text-foreground mb-2">Company Profile</h2>
          <p className="text-muted-foreground">Manage your company's compliance information, addresses, and default shipping details.</p>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={(value) => setActiveTab(value as typeof activeTab)} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="compliance" className="flex items-center gap-2">
            <FileCheck className="w-4 h-4" /> Compliance
          </TabsTrigger>
          <TabsTrigger value="addresses" className="flex items-center gap-2">
            <MapPin className="w-4 h-4" /> Address Book ({addresses.length})
          </TabsTrigger>
          <TabsTrigger value="consignee-shipper" className="flex items-center gap-2">
            <Building2 className="w-4 h-4" /> Default Consignee/Shipper ({consigneeShipper.length})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="compliance" className="mt-6">
          <ComplianceTab
            complianceInfo={complianceInfo}
            loading={loading}
            onSave={handleSaveCompliance}
            dialogOpen={complianceDialogOpen}
            onDialogOpenChange={setComplianceDialogOpen}
          />
        </TabsContent>

        <TabsContent value="addresses" className="mt-6">
          <AddressBookTab
            addresses={addresses}
            loading={loading}
            onSave={handleSaveAddress}
            onDelete={handleDeleteAddress}
            dialogOpen={addressDialogOpen}
            onDialogOpenChange={setAddressDialogOpen}
            editingAddress={editingAddress}
            onEdit={setEditingAddress}
          />
        </TabsContent>

        <TabsContent value="consignee-shipper" className="mt-6">
          <ConsigneeShipperTab
            consigneeShipper={consigneeShipper}
            addresses={addresses}
            loading={loading}
            onSave={handleSaveConsigneeShipper}
            onDelete={handleDeleteConsigneeShipper}
            dialogOpen={consigneeShipperDialogOpen}
            onDialogOpenChange={setConsigneeShipperDialogOpen}
            editingConsigneeShipper={editingConsigneeShipper}
            onEdit={setEditingConsigneeShipper}
          />
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Compliance Tab Component
function ComplianceTab({
  complianceInfo,
  loading,
  onSave,
  dialogOpen,
  onDialogOpenChange,
}: {
  complianceInfo: CompanyComplianceInfo | null;
  loading: boolean;
  onSave: (data: CompanyComplianceInfoCreate) => Promise<void>;
  dialogOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
}) {
  const [formData, setFormData] = React.useState<CompanyComplianceInfoCreate>({
    company_id: "",
    tax_id: complianceInfo?.tax_id || "",
    vat_number: complianceInfo?.vat_number || "",
    registration_number: complianceInfo?.registration_number || "",
    regulator_id: complianceInfo?.regulator_id || "",
    compliance_status: complianceInfo?.compliance_status || "pending",
    expiry_date: complianceInfo?.expiry_date || undefined,
    notes: complianceInfo?.notes || "",
  });

  React.useEffect(() => {
    if (complianceInfo) {
      setFormData({
        company_id: complianceInfo.company_id,
        tax_id: complianceInfo.tax_id || "",
        vat_number: complianceInfo.vat_number || "",
        registration_number: complianceInfo.registration_number || "",
        regulator_id: complianceInfo.regulator_id || "",
        compliance_status: complianceInfo.compliance_status,
        expiry_date: complianceInfo.expiry_date || undefined,
        notes: complianceInfo.notes || "",
      });
    }
  }, [complianceInfo]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "verified":
        return <CheckCircle2 className="w-5 h-5 text-success" />;
      case "expired":
        return <AlertCircle className="w-5 h-5 text-warning" />;
      case "rejected":
        return <XCircle className="w-5 h-5 text-destructive" />;
      default:
        return <Clock className="w-5 h-5 text-muted-foreground" />;
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Compliance Information</CardTitle>
            <CardDescription>Manage your company's tax IDs, registration numbers, and compliance status.</CardDescription>
          </div>
          <Button onClick={() => onDialogOpenChange(true)}>
            <Edit className="w-4 h-4 mr-2" /> Edit
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        ) : complianceInfo ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="text-muted-foreground">Tax ID / TIN</Label>
                <p className="text-sm font-medium">{complianceInfo.tax_id || "Not provided"}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">VAT Number</Label>
                <p className="text-sm font-medium">{complianceInfo.vat_number || "Not provided"}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Registration Number</Label>
                <p className="text-sm font-medium">{complianceInfo.registration_number || "Not provided"}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Regulator ID</Label>
                <p className="text-sm font-medium">{complianceInfo.regulator_id || "Not provided"}</p>
              </div>
              <div>
                <Label className="text-muted-foreground">Compliance Status</Label>
                <div className="flex items-center gap-2 mt-1">
                  {getStatusIcon(complianceInfo.compliance_status)}
                  <StatusBadge
                    status={
                      complianceInfo.compliance_status === "verified"
                        ? "success"
                        : complianceInfo.compliance_status === "rejected"
                        ? "destructive"
                        : complianceInfo.compliance_status === "expired"
                        ? "warning"
                        : "info"
                    }
                  >
                    {complianceInfo.compliance_status}
                  </StatusBadge>
                </div>
              </div>
              {complianceInfo.expiry_date && (
                <div>
                  <Label className="text-muted-foreground">Expiry Date</Label>
                  <p className="text-sm font-medium">{new Date(complianceInfo.expiry_date).toLocaleDateString()}</p>
                </div>
              )}
            </div>
            {complianceInfo.notes && (
              <div>
                <Label className="text-muted-foreground">Notes</Label>
                <p className="text-sm text-muted-foreground mt-1">{complianceInfo.notes}</p>
              </div>
            )}
          </div>
        ) : (
          <div className="text-center py-8 text-muted-foreground">
            <FileCheck className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>No compliance information set up</p>
            <Button onClick={() => onDialogOpenChange(true)} className="mt-4">
              <Plus className="w-4 h-4 mr-2" /> Add Compliance Information
            </Button>
          </div>
        )}
      </CardContent>

      <ComplianceDialog
        open={dialogOpen}
        onOpenChange={onDialogOpenChange}
        complianceInfo={complianceInfo}
        onSave={onSave}
      />
    </Card>
  );
}

// Compliance Dialog Component
function ComplianceDialog({
  open,
  onOpenChange,
  complianceInfo,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  complianceInfo: CompanyComplianceInfo | null;
  onSave: (data: CompanyComplianceInfoCreate) => Promise<void>;
}) {
  const [formData, setFormData] = React.useState<CompanyComplianceInfoCreate>({
    company_id: complianceInfo?.company_id || "",
    tax_id: complianceInfo?.tax_id || "",
    vat_number: complianceInfo?.vat_number || "",
    registration_number: complianceInfo?.registration_number || "",
    regulator_id: complianceInfo?.regulator_id || "",
    compliance_status: complianceInfo?.compliance_status || "pending",
    expiry_date: complianceInfo?.expiry_date || undefined,
    notes: complianceInfo?.notes || "",
  });
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (complianceInfo) {
      setFormData({
        company_id: complianceInfo.company_id,
        tax_id: complianceInfo.tax_id || "",
        vat_number: complianceInfo.vat_number || "",
        registration_number: complianceInfo.registration_number || "",
        regulator_id: complianceInfo.regulator_id || "",
        compliance_status: complianceInfo.compliance_status,
        expiry_date: complianceInfo.expiry_date || undefined,
        notes: complianceInfo.notes || "",
      });
    }
  }, [complianceInfo, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{complianceInfo ? "Edit" : "Add"} Compliance Information</DialogTitle>
          <DialogDescription>Enter your company's compliance and regulatory information.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="tax_id">Tax ID / TIN</Label>
              <Input
                id="tax_id"
                value={formData.tax_id}
                onChange={(e) => setFormData({ ...formData, tax_id: e.target.value })}
                placeholder="Enter tax ID"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="vat_number">VAT Number</Label>
              <Input
                id="vat_number"
                value={formData.vat_number}
                onChange={(e) => setFormData({ ...formData, vat_number: e.target.value })}
                placeholder="Enter VAT number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="registration_number">Registration Number</Label>
              <Input
                id="registration_number"
                value={formData.registration_number}
                onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                placeholder="Enter registration number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="regulator_id">Regulator ID</Label>
              <Input
                id="regulator_id"
                value={formData.regulator_id}
                onChange={(e) => setFormData({ ...formData, regulator_id: e.target.value })}
                placeholder="Enter regulator ID"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="compliance_status">Compliance Status</Label>
              <Select
                value={formData.compliance_status}
                onValueChange={(value: "pending" | "verified" | "expired" | "rejected") =>
                  setFormData({ ...formData, compliance_status: value })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="verified">Verified</SelectItem>
                  <SelectItem value="expired">Expired</SelectItem>
                  <SelectItem value="rejected">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="expiry_date">Expiry Date</Label>
              <Input
                id="expiry_date"
                type="date"
                value={formData.expiry_date ? new Date(formData.expiry_date).toISOString().split("T")[0] : ""}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    expiry_date: e.target.value ? new Date(e.target.value).toISOString() : undefined,
                  })
                }
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="notes">Notes</Label>
            <Textarea
              id="notes"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              placeholder="Additional notes or comments"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Address Book Tab Component (simplified - will continue in next part)
function AddressBookTab({
  addresses,
  loading,
  onSave,
  onDelete,
  dialogOpen,
  onDialogOpenChange,
  editingAddress,
  onEdit,
}: {
  addresses: CompanyAddress[];
  loading: boolean;
  onSave: (data: CompanyAddressCreate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  dialogOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
  editingAddress: CompanyAddress | null;
  onEdit: (address: CompanyAddress | null) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Address Book</CardTitle>
            <CardDescription>Manage your company's addresses for shipping, billing, and business operations.</CardDescription>
          </div>
          <Button
            onClick={() => {
              onEdit(null);
              onDialogOpenChange(true);
            }}
          >
            <Plus className="w-4 h-4 mr-2" /> Add Address
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        ) : addresses.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <MapPin className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>No addresses added yet</p>
            <Button
              onClick={() => {
                onEdit(null);
                onDialogOpenChange(true);
              }}
              className="mt-4"
            >
              <Plus className="w-4 h-4 mr-2" /> Add First Address
            </Button>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Label</TableHead>
                <TableHead>Type</TableHead>
                <TableHead>Address</TableHead>
                <TableHead>Contact</TableHead>
                <TableHead>Defaults</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {addresses.map((address) => (
                <TableRow key={address.id}>
                  <TableCell className="font-medium">{address.label}</TableCell>
                  <TableCell>
                    <StatusBadge status="info">{address.address_type}</StatusBadge>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">
                      {address.street_address}
                      <br />
                      {address.city}, {address.state_province || ""} {address.postal_code || ""}
                      <br />
                      {address.country}
                    </div>
                  </TableCell>
                  <TableCell>
                    {address.contact_name && (
                      <div className="text-sm">
                        {address.contact_name}
                        {address.contact_email && <div className="text-muted-foreground">{address.contact_email}</div>}
                      </div>
                    )}
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-2">
                      {address.is_default_shipping && (
                        <StatusBadge status="success" className="text-xs">Shipping</StatusBadge>
                      )}
                      {address.is_default_billing && (
                        <StatusBadge status="success" className="text-xs">Billing</StatusBadge>
                      )}
                    </div>
                  </TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => {
                          onEdit(address);
                          onDialogOpenChange(true);
                        }}
                      >
                        <Edit className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onDelete(address.id)}
                        className="text-destructive hover:text-destructive"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>

      <AddressDialog
        open={dialogOpen}
        onOpenChange={onDialogOpenChange}
        address={editingAddress}
        onSave={onSave}
      />
    </Card>
  );
}

// Address Dialog Component (simplified - full implementation would be similar to ComplianceDialog)
function AddressDialog({
  open,
  onOpenChange,
  address,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  address: CompanyAddress | null;
  onSave: (data: CompanyAddressCreate) => Promise<void>;
}) {
  const [formData, setFormData] = React.useState<CompanyAddressCreate>({
    company_id: "",
    label: "",
    address_type: "business",
    street_address: "",
    city: "",
    state_province: "",
    postal_code: "",
    country: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    is_default_shipping: false,
    is_default_billing: false,
  });
  const [saving, setSaving] = React.useState(false);

  React.useEffect(() => {
    if (address) {
      setFormData({
        company_id: address.company_id,
        label: address.label,
        address_type: address.address_type,
        street_address: address.street_address,
        city: address.city,
        state_province: address.state_province || "",
        postal_code: address.postal_code || "",
        country: address.country,
        contact_name: address.contact_name || "",
        contact_email: address.contact_email || "",
        contact_phone: address.contact_phone || "",
        is_default_shipping: address.is_default_shipping,
        is_default_billing: address.is_default_billing,
      });
    } else {
      setFormData({
        company_id: "",
        label: "",
        address_type: "business",
        street_address: "",
        city: "",
        state_province: "",
        postal_code: "",
        country: "",
        contact_name: "",
        contact_email: "",
        contact_phone: "",
        is_default_shipping: false,
        is_default_billing: false,
      });
    }
  }, [address, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await onSave(formData);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{address ? "Edit" : "Add"} Address</DialogTitle>
          <DialogDescription>Enter address details for your company.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="label">Label *</Label>
              <Input
                id="label"
                value={formData.label}
                onChange={(e) => setFormData({ ...formData, label: e.target.value })}
                placeholder="e.g., Main Warehouse"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="address_type">Address Type *</Label>
              <Select
                value={formData.address_type}
                onValueChange={(value: any) => setFormData({ ...formData, address_type: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="business">Business</SelectItem>
                  <SelectItem value="shipping">Shipping</SelectItem>
                  <SelectItem value="billing">Billing</SelectItem>
                  <SelectItem value="warehouse">Warehouse</SelectItem>
                  <SelectItem value="custom">Custom</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="street_address">Street Address *</Label>
            <Textarea
              id="street_address"
              value={formData.street_address}
              onChange={(e) => setFormData({ ...formData, street_address: e.target.value })}
              placeholder="Enter street address"
              required
              rows={2}
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="city">City *</Label>
              <Input
                id="city"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                placeholder="City"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="state_province">State/Province</Label>
              <Input
                id="state_province"
                value={formData.state_province}
                onChange={(e) => setFormData({ ...formData, state_province: e.target.value })}
                placeholder="State/Province"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="postal_code">Postal Code</Label>
              <Input
                id="postal_code"
                value={formData.postal_code}
                onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                placeholder="Postal Code"
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="country">Country *</Label>
            <Input
              id="country"
              value={formData.country}
              onChange={(e) => setFormData({ ...formData, country: e.target.value })}
              placeholder="Country"
              required
            />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input
                id="contact_name"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                placeholder="Contact name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_email">Contact Email</Label>
              <Input
                id="contact_email"
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                placeholder="contact@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Contact Phone</Label>
              <Input
                id="contact_phone"
                value={formData.contact_phone}
                onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                placeholder="+1 234 567 8900"
              />
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_default_shipping"
                checked={formData.is_default_shipping}
                onCheckedChange={(checked) => setFormData({ ...formData, is_default_shipping: checked === true })}
              />
              <Label htmlFor="is_default_shipping" className="cursor-pointer">
                Default Shipping Address
              </Label>
            </div>
            <div className="flex items-center space-x-2">
              <Checkbox
                id="is_default_billing"
                checked={formData.is_default_billing}
                onCheckedChange={(checked) => setFormData({ ...formData, is_default_billing: checked === true })}
              />
              <Label htmlFor="is_default_billing" className="cursor-pointer">
                Default Billing Address
              </Label>
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

// Consignee/Shipper Tab Component (simplified)
function ConsigneeShipperTab({
  consigneeShipper,
  addresses,
  loading,
  onSave,
  onDelete,
  dialogOpen,
  onDialogOpenChange,
  editingConsigneeShipper,
  onEdit,
}: {
  consigneeShipper: DefaultConsigneeShipper[];
  addresses: CompanyAddress[];
  loading: boolean;
  onSave: (data: DefaultConsigneeShipperCreate) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
  dialogOpen: boolean;
  onDialogOpenChange: (open: boolean) => void;
  editingConsigneeShipper: DefaultConsigneeShipper | null;
  onEdit: (cs: DefaultConsigneeShipper | null) => void;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Default Consignee/Shipper</CardTitle>
            <CardDescription>Set default consignee (for exporters) or shipper (for importers) information to pre-fill forms.</CardDescription>
          </div>
          <Button
            onClick={() => {
              onEdit(null);
              onDialogOpenChange(true);
            }}
          >
            <Plus className="w-4 h-4 mr-2" /> Add Default
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        ) : consigneeShipper.length === 0 ? (
          <div className="text-center py-8 text-muted-foreground">
            <Building2 className="w-12 h-12 mx-auto mb-4 opacity-20" />
            <p>No default consignee/shipper set up</p>
            <Button
              onClick={() => {
                onEdit(null);
                onDialogOpenChange(true);
              }}
              className="mt-4"
            >
              <Plus className="w-4 h-4 mr-2" /> Add Default Consignee/Shipper
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {consigneeShipper.map((cs) => (
              <Card key={cs.id} className="p-4">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <StatusBadge status={cs.type_ === "consignee" ? "info" : "success"}>
                        {cs.type_}
                      </StatusBadge>
                      <h4 className="font-semibold">{cs.company_name}</h4>
                    </div>
                    {cs.contact_name && (
                      <p className="text-sm text-muted-foreground">
                        Contact: {cs.contact_name}
                        {cs.contact_email && ` (${cs.contact_email})`}
                      </p>
                    )}
                    {(cs.street_address || cs.address_id) && (
                      <p className="text-sm text-muted-foreground mt-1">
                        {cs.street_address || "Address from address book"}
                        {cs.city && `, ${cs.city}`}
                        {cs.country && `, ${cs.country}`}
                      </p>
                    )}
                    {cs.bank_name && (
                      <p className="text-sm text-muted-foreground mt-1">
                        Bank: {cs.bank_name}
                        {cs.swift_code && ` (SWIFT: ${cs.swift_code})`}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => {
                        onEdit(cs);
                        onDialogOpenChange(true);
                      }}
                    >
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onDelete(cs.id)}
                      className="text-destructive hover:text-destructive"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </CardContent>

      <ConsigneeShipperDialog
        open={dialogOpen}
        onOpenChange={onDialogOpenChange}
        consigneeShipper={editingConsigneeShipper}
        addresses={addresses}
        onSave={onSave}
      />
    </Card>
  );
}

// Consignee/Shipper Dialog Component (simplified)
function ConsigneeShipperDialog({
  open,
  onOpenChange,
  consigneeShipper,
  addresses,
  onSave,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  consigneeShipper: DefaultConsigneeShipper | null;
  addresses: CompanyAddress[];
  onSave: (data: DefaultConsigneeShipperCreate) => Promise<void>;
}) {
  const [formData, setFormData] = React.useState<DefaultConsigneeShipperCreate>({
    company_id: "",
    type_: "consignee",
    company_name: "",
    contact_name: "",
    contact_email: "",
    contact_phone: "",
    address_id: undefined,
    street_address: "",
    city: "",
    state_province: "",
    postal_code: "",
    country: "",
    bank_name: "",
    bank_account: "",
    swift_code: "",
  });
  const [saving, setSaving] = React.useState(false);
  const [useAddressBook, setUseAddressBook] = React.useState(false);

  React.useEffect(() => {
    if (consigneeShipper) {
      setFormData({
        company_id: consigneeShipper.company_id,
        type_: consigneeShipper.type_,
        company_name: consigneeShipper.company_name,
        contact_name: consigneeShipper.contact_name || "",
        contact_email: consigneeShipper.contact_email || "",
        contact_phone: consigneeShipper.contact_phone || "",
        address_id: consigneeShipper.address_id || undefined,
        street_address: consigneeShipper.street_address || "",
        city: consigneeShipper.city || "",
        state_province: consigneeShipper.state_province || "",
        postal_code: consigneeShipper.postal_code || "",
        country: consigneeShipper.country || "",
        bank_name: consigneeShipper.bank_name || "",
        bank_account: consigneeShipper.bank_account || "",
        swift_code: consigneeShipper.swift_code || "",
      });
      setUseAddressBook(!!consigneeShipper.address_id);
    } else {
      setFormData({
        company_id: "",
        type_: "consignee",
        company_name: "",
        contact_name: "",
        contact_email: "",
        contact_phone: "",
        address_id: undefined,
        street_address: "",
        city: "",
        state_province: "",
        postal_code: "",
        country: "",
        bank_name: "",
        bank_account: "",
        swift_code: "",
      });
      setUseAddressBook(false);
    }
  }, [consigneeShipper, open]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const dataToSave = { ...formData };
      if (useAddressBook && formData.address_id) {
        // Clear manual address fields if using address book
        dataToSave.street_address = undefined;
        dataToSave.city = undefined;
        dataToSave.state_province = undefined;
        dataToSave.postal_code = undefined;
        dataToSave.country = undefined;
      } else {
        // Clear address_id if using manual address
        dataToSave.address_id = undefined;
      }
      await onSave(dataToSave);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{consigneeShipper ? "Edit" : "Add"} Default Consignee/Shipper</DialogTitle>
          <DialogDescription>Enter default consignee (for exporters) or shipper (for importers) information.</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="type_">Type *</Label>
              <Select
                value={formData.type_}
                onValueChange={(value: "consignee" | "shipper") => setFormData({ ...formData, type_: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="consignee">Consignee (for Exporters)</SelectItem>
                  <SelectItem value="shipper">Shipper (for Importers)</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="company_name">Company Name *</Label>
              <Input
                id="company_name"
                value={formData.company_name}
                onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                placeholder="Company name"
                required
              />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="contact_name">Contact Name</Label>
              <Input
                id="contact_name"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
                placeholder="Contact name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_email">Contact Email</Label>
              <Input
                id="contact_email"
                type="email"
                value={formData.contact_email}
                onChange={(e) => setFormData({ ...formData, contact_email: e.target.value })}
                placeholder="contact@example.com"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="contact_phone">Contact Phone</Label>
              <Input
                id="contact_phone"
                value={formData.contact_phone}
                onChange={(e) => setFormData({ ...formData, contact_phone: e.target.value })}
                placeholder="+1 234 567 8900"
              />
            </div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="use_address_book"
                checked={useAddressBook}
                onCheckedChange={(checked) => {
                  setUseAddressBook(checked === true);
                  if (!checked) {
                    setFormData({ ...formData, address_id: undefined });
                  }
                }}
              />
              <Label htmlFor="use_address_book" className="cursor-pointer">
                Use address from address book
              </Label>
            </div>
          </div>
          {useAddressBook ? (
            <div className="space-y-2">
              <Label htmlFor="address_id">Select Address</Label>
              <Select
                value={formData.address_id || ""}
                onValueChange={(value) => setFormData({ ...formData, address_id: value as any })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select an address" />
                </SelectTrigger>
                <SelectContent>
                  {addresses.map((addr) => (
                    <SelectItem key={addr.id} value={addr.id}>
                      {addr.label} - {addr.city}, {addr.country}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ) : (
            <>
              <div className="space-y-2">
                <Label htmlFor="street_address">Street Address</Label>
                <Textarea
                  id="street_address"
                  value={formData.street_address}
                  onChange={(e) => setFormData({ ...formData, street_address: e.target.value })}
                  placeholder="Enter street address"
                  rows={2}
                />
              </div>
              <div className="grid grid-cols-3 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="city">City</Label>
                  <Input
                    id="city"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="City"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="state_province">State/Province</Label>
                  <Input
                    id="state_province"
                    value={formData.state_province}
                    onChange={(e) => setFormData({ ...formData, state_province: e.target.value })}
                    placeholder="State/Province"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="postal_code">Postal Code</Label>
                  <Input
                    id="postal_code"
                    value={formData.postal_code}
                    onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                    placeholder="Postal Code"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="country">Country</Label>
                <Input
                  id="country"
                  value={formData.country}
                  onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                  placeholder="Country"
                />
              </div>
            </>
          )}
          <div className="grid grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="bank_name">Bank Name</Label>
              <Input
                id="bank_name"
                value={formData.bank_name}
                onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                placeholder="Bank name"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bank_account">Bank Account</Label>
              <Input
                id="bank_account"
                value={formData.bank_account}
                onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })}
                placeholder="Account number"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="swift_code">SWIFT Code</Label>
              <Input
                id="swift_code"
                value={formData.swift_code}
                onChange={(e) => setFormData({ ...formData, swift_code: e.target.value })}
                placeholder="SWIFT/BIC"
              />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? "Saving..." : "Save"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

