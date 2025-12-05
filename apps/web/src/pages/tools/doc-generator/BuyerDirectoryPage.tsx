/**
 * Buyer Directory Page
 * 
 * Manage frequent buyers/applicants for quick selection
 */

import { useState, useEffect } from "react";
import {
  Users,
  Plus,
  Edit,
  Trash2,
  Loader2,
  Search,
  MoreHorizontal,
  Building2,
  MapPin,
  Mail,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Buyer {
  id: string;
  buyer_code: string | null;
  company_name: string;
  country: string | null;
  address_line1: string | null;
  city: string | null;
  contact_person: string | null;
  email: string | null;
  preferred_incoterms: string | null;
  default_currency: string;
  is_active: boolean;
  use_count: number;
}

interface BuyerForm {
  buyer_code: string;
  company_name: string;
  country: string;
  address_line1: string;
  address_line2: string;
  city: string;
  state: string;
  postal_code: string;
  contact_person: string;
  email: string;
  phone: string;
  notify_party_name: string;
  notify_party_address: string;
  preferred_incoterms: string;
  preferred_port_of_discharge: string;
  default_currency: string;
  buyer_bank_name: string;
  buyer_bank_swift: string;
  notes: string;
}

const emptyForm: BuyerForm = {
  buyer_code: "",
  company_name: "",
  country: "",
  address_line1: "",
  address_line2: "",
  city: "",
  state: "",
  postal_code: "",
  contact_person: "",
  email: "",
  phone: "",
  notify_party_name: "",
  notify_party_address: "",
  preferred_incoterms: "",
  preferred_port_of_discharge: "",
  default_currency: "USD",
  buyer_bank_name: "",
  buyer_bank_swift: "",
  notes: "",
};

const INCOTERMS = ["FOB", "CIF", "CFR", "CIP", "DAP", "DDP", "EXW", "FCA"];

export function BuyerDirectoryPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [buyers, setBuyers] = useState<Buyer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<BuyerForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchBuyers();
  }, []);

  const fetchBuyers = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/directory/buyers`, {
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      if (response.ok) {
        setBuyers(await response.json());
      }
    } catch (error) {
      console.error("Error fetching buyers:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!form.company_name.trim()) {
      toast({ title: "Error", description: "Company name is required", variant: "destructive" });
      return;
    }

    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId 
        ? `${API_BASE}/api/doc-generator/directory/buyers/${editingId}`
        : `${API_BASE}/api/doc-generator/directory/buyers`;

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify(form),
      });

      if (!response.ok) throw new Error("Failed to save");

      toast({ title: editingId ? "Updated" : "Created", description: "Buyer saved successfully" });
      setDialogOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      fetchBuyers();
    } catch (error) {
      toast({ title: "Error", description: "Failed to save buyer", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this buyer from directory?")) return;
    
    try {
      await fetch(`${API_BASE}/api/doc-generator/directory/buyers/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      toast({ title: "Removed", description: "Buyer removed from directory" });
      fetchBuyers();
    } catch (error) {
      toast({ title: "Error", description: "Failed to remove", variant: "destructive" });
    }
  };

  const openEdit = (buyer: Buyer) => {
    setEditingId(buyer.id);
    setForm({
      buyer_code: buyer.buyer_code || "",
      company_name: buyer.company_name,
      country: buyer.country || "",
      address_line1: buyer.address_line1 || "",
      address_line2: "",
      city: buyer.city || "",
      state: "",
      postal_code: "",
      contact_person: buyer.contact_person || "",
      email: buyer.email || "",
      phone: "",
      notify_party_name: "",
      notify_party_address: "",
      preferred_incoterms: buyer.preferred_incoterms || "",
      preferred_port_of_discharge: "",
      default_currency: buyer.default_currency,
      buyer_bank_name: "",
      buyer_bank_swift: "",
      notes: "",
    });
    setDialogOpen(true);
  };

  const filteredBuyers = buyers.filter(b =>
    b.company_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.buyer_code?.toLowerCase().includes(searchQuery.toLowerCase()) ||
    b.country?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Buyer Directory</h1>
          <p className="text-slate-400">Save frequent buyers for quick document creation</p>
        </div>
        <Button onClick={() => { setEditingId(null); setForm(emptyForm); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Buyer
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search by name, code, or country..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 bg-slate-800 border-slate-700"
        />
      </div>

      {/* Buyers Table */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : filteredBuyers.length === 0 ? (
            <div className="text-center p-12">
              <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No buyers in directory</h3>
              <p className="text-slate-400 mb-4">Add buyers to auto-fill applicant details</p>
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add First Buyer
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800">
                  <TableHead className="text-slate-400">Company</TableHead>
                  <TableHead className="text-slate-400">Country</TableHead>
                  <TableHead className="text-slate-400">Contact</TableHead>
                  <TableHead className="text-slate-400">Incoterms</TableHead>
                  <TableHead className="text-slate-400">Currency</TableHead>
                  <TableHead className="text-slate-400">Uses</TableHead>
                  <TableHead className="text-slate-400 w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredBuyers.map((buyer) => (
                  <TableRow key={buyer.id} className="border-slate-800 hover:bg-slate-800/50">
                    <TableCell className="text-white">
                      <div className="flex items-start gap-2">
                        <Building2 className="w-4 h-4 text-slate-400 mt-1 flex-shrink-0" />
                        <div>
                          <div className="font-medium">{buyer.company_name}</div>
                          {buyer.buyer_code && (
                            <span className="text-xs text-slate-400">Code: {buyer.buyer_code}</span>
                          )}
                          {buyer.city && (
                            <div className="flex items-center gap-1 text-xs text-slate-400 mt-1">
                              <MapPin className="w-3 h-3" />
                              {buyer.city}
                            </div>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {buyer.country ? (
                        <Badge variant="outline">{buyer.country}</Badge>
                      ) : (
                        <span className="text-slate-500">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-300">
                      <div className="space-y-1">
                        {buyer.contact_person && <div>{buyer.contact_person}</div>}
                        {buyer.email && (
                          <div className="flex items-center gap-1 text-xs text-slate-400">
                            <Mail className="w-3 h-3" />
                            {buyer.email}
                          </div>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-slate-300">{buyer.preferred_incoterms || "-"}</TableCell>
                    <TableCell className="text-slate-300">{buyer.default_currency}</TableCell>
                    <TableCell className="text-slate-300">{buyer.use_count}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(buyer)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(buyer.id)}
                            className="text-red-500"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
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
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Buyer" : "Add Buyer"}</DialogTitle>
            <DialogDescription>
              Save buyer details for quick applicant selection
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Company Info */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Buyer Code</Label>
                <Input
                  value={form.buyer_code}
                  onChange={(e) => setForm({ ...form, buyer_code: e.target.value })}
                  placeholder="BUYER-001"
                />
              </div>
              <div className="space-y-2 col-span-2">
                <Label>Company Name *</Label>
                <Input
                  value={form.company_name}
                  onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                  placeholder="Acme Imports Inc."
                />
              </div>
            </div>

            {/* Address */}
            <div className="space-y-2">
              <Label>Address Line 1</Label>
              <Input
                value={form.address_line1}
                onChange={(e) => setForm({ ...form, address_line1: e.target.value })}
                placeholder="123 Import Street"
              />
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>City</Label>
                <Input
                  value={form.city}
                  onChange={(e) => setForm({ ...form, city: e.target.value })}
                  placeholder="New York"
                />
              </div>
              <div className="space-y-2">
                <Label>State/Province</Label>
                <Input
                  value={form.state}
                  onChange={(e) => setForm({ ...form, state: e.target.value })}
                  placeholder="NY"
                />
              </div>
              <div className="space-y-2">
                <Label>Postal Code</Label>
                <Input
                  value={form.postal_code}
                  onChange={(e) => setForm({ ...form, postal_code: e.target.value })}
                  placeholder="10001"
                />
              </div>
              <div className="space-y-2">
                <Label>Country</Label>
                <Input
                  value={form.country}
                  onChange={(e) => setForm({ ...form, country: e.target.value })}
                  placeholder="USA"
                />
              </div>
            </div>

            {/* Contact */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Contact Person</Label>
                <Input
                  value={form.contact_person}
                  onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
                  placeholder="John Smith"
                />
              </div>
              <div className="space-y-2">
                <Label>Email</Label>
                <Input
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm({ ...form, email: e.target.value })}
                  placeholder="john@acme.com"
                />
              </div>
              <div className="space-y-2">
                <Label>Phone</Label>
                <Input
                  value={form.phone}
                  onChange={(e) => setForm({ ...form, phone: e.target.value })}
                  placeholder="+1 234 567 8900"
                />
              </div>
            </div>

            {/* Notify Party */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Notify Party Name</Label>
                <Input
                  value={form.notify_party_name}
                  onChange={(e) => setForm({ ...form, notify_party_name: e.target.value })}
                  placeholder="Same as buyer or different"
                />
              </div>
              <div className="space-y-2">
                <Label>Notify Party Address</Label>
                <Input
                  value={form.notify_party_address}
                  onChange={(e) => setForm({ ...form, notify_party_address: e.target.value })}
                  placeholder="Address if different"
                />
              </div>
            </div>

            {/* Trade Preferences */}
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Preferred Incoterms</Label>
                <Select value={form.preferred_incoterms} onValueChange={(v) => setForm({ ...form, preferred_incoterms: v })}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select..." />
                  </SelectTrigger>
                  <SelectContent>
                    {INCOTERMS.map((term) => (
                      <SelectItem key={term} value={term}>{term}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Default Currency</Label>
                <Select value={form.default_currency} onValueChange={(v) => setForm({ ...form, default_currency: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="USD">USD</SelectItem>
                    <SelectItem value="EUR">EUR</SelectItem>
                    <SelectItem value="GBP">GBP</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Port of Discharge</Label>
                <Input
                  value={form.preferred_port_of_discharge}
                  onChange={(e) => setForm({ ...form, preferred_port_of_discharge: e.target.value })}
                  placeholder="New York, USA"
                />
              </div>
            </div>

            {/* Banking */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Buyer's Bank Name</Label>
                <Input
                  value={form.buyer_bank_name}
                  onChange={(e) => setForm({ ...form, buyer_bank_name: e.target.value })}
                  placeholder="Bank of America"
                />
              </div>
              <div className="space-y-2">
                <Label>SWIFT Code</Label>
                <Input
                  value={form.buyer_bank_swift}
                  onChange={(e) => setForm({ ...form, buyer_bank_swift: e.target.value })}
                  placeholder="BOFAUS3N"
                />
              </div>
            </div>

            {/* Notes */}
            <div className="space-y-2">
              <Label>Notes</Label>
              <Textarea
                value={form.notes}
                onChange={(e) => setForm({ ...form, notes: e.target.value })}
                placeholder="Any special instructions or notes about this buyer..."
                rows={2}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editingId ? "Update" : "Add Buyer"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default BuyerDirectoryPage;

