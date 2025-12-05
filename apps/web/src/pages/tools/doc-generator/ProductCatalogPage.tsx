/**
 * Product Catalog Page
 * 
 * Manage frequently shipped products with HS codes and pricing
 */

import { useState, useEffect } from "react";
import {
  Package,
  Plus,
  Edit,
  Trash2,
  Loader2,
  Search,
  MoreHorizontal,
  Tag,
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

interface Product {
  id: string;
  sku: string | null;
  product_code: string | null;
  name: string;
  hs_code: string | null;
  description: string;
  short_description: string | null;
  default_unit_price: number | null;
  currency: string;
  default_unit: string;
  units_per_carton: number | null;
  weight_per_unit_kg: number | null;
  country_of_origin: string | null;
  is_active: boolean;
  use_count: number;
}

interface ProductForm {
  sku: string;
  product_code: string;
  name: string;
  hs_code: string;
  description: string;
  short_description: string;
  default_unit_price: string;
  currency: string;
  default_unit: string;
  units_per_carton: string;
  weight_per_unit_kg: string;
  carton_dimensions: string;
  carton_weight_kg: string;
  country_of_origin: string;
}

const emptyForm: ProductForm = {
  sku: "",
  product_code: "",
  name: "",
  hs_code: "",
  description: "",
  short_description: "",
  default_unit_price: "",
  currency: "USD",
  default_unit: "PCS",
  units_per_carton: "",
  weight_per_unit_kg: "",
  carton_dimensions: "",
  carton_weight_kg: "",
  country_of_origin: "",
};

const UNIT_OPTIONS = ["PCS", "KG", "MT", "MTR", "YDS", "SET", "DOZ", "CTN", "PKG", "UNIT"];

export function ProductCatalogPage() {
  const { toast } = useToast();
  const { user } = useAuth();
  
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<ProductForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await fetch(`${API_BASE}/api/doc-generator/catalog/products`, {
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      if (response.ok) {
        setProducts(await response.json());
      }
    } catch (error) {
      console.error("Error fetching products:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!form.name.trim() || !form.description.trim()) {
      toast({ title: "Error", description: "Name and description are required", variant: "destructive" });
      return;
    }

    setSaving(true);
    try {
      const method = editingId ? "PUT" : "POST";
      const url = editingId 
        ? `${API_BASE}/api/doc-generator/catalog/products/${editingId}`
        : `${API_BASE}/api/doc-generator/catalog/products`;

      const payload = {
        ...form,
        default_unit_price: form.default_unit_price ? parseFloat(form.default_unit_price) : null,
        units_per_carton: form.units_per_carton ? parseInt(form.units_per_carton) : null,
        weight_per_unit_kg: form.weight_per_unit_kg ? parseFloat(form.weight_per_unit_kg) : null,
        carton_weight_kg: form.carton_weight_kg ? parseFloat(form.carton_weight_kg) : null,
      };

      const response = await fetch(url, {
        method,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${user?.access_token || ""}`,
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error("Failed to save");

      toast({ title: editingId ? "Updated" : "Created", description: "Product saved successfully" });
      setDialogOpen(false);
      setEditingId(null);
      setForm(emptyForm);
      fetchProducts();
    } catch (error) {
      toast({ title: "Error", description: "Failed to save product", variant: "destructive" });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Remove this product from catalog?")) return;
    
    try {
      await fetch(`${API_BASE}/api/doc-generator/catalog/products/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${user?.access_token || ""}` },
      });
      toast({ title: "Removed", description: "Product removed from catalog" });
      fetchProducts();
    } catch (error) {
      toast({ title: "Error", description: "Failed to remove", variant: "destructive" });
    }
  };

  const openEdit = (product: Product) => {
    setEditingId(product.id);
    setForm({
      sku: product.sku || "",
      product_code: product.product_code || "",
      name: product.name,
      hs_code: product.hs_code || "",
      description: product.description,
      short_description: product.short_description || "",
      default_unit_price: product.default_unit_price?.toString() || "",
      currency: product.currency,
      default_unit: product.default_unit,
      units_per_carton: product.units_per_carton?.toString() || "",
      weight_per_unit_kg: product.weight_per_unit_kg?.toString() || "",
      carton_dimensions: "",
      carton_weight_kg: "",
      country_of_origin: product.country_of_origin || "",
    });
    setDialogOpen(true);
  };

  const filteredProducts = products.filter(p =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    p.hs_code?.includes(searchQuery) ||
    p.sku?.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Product Catalog</h1>
          <p className="text-slate-400">Save frequently shipped products for quick entry</p>
        </div>
        <Button onClick={() => { setEditingId(null); setForm(emptyForm); setDialogOpen(true); }}>
          <Plus className="w-4 h-4 mr-2" />
          Add Product
        </Button>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Search by name, SKU, or HS code..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10 bg-slate-800 border-slate-700"
        />
      </div>

      {/* Products Table */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
            </div>
          ) : filteredProducts.length === 0 ? (
            <div className="text-center p-12">
              <Package className="h-12 w-12 text-slate-600 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-white mb-2">No products in catalog</h3>
              <p className="text-slate-400 mb-4">Add products to speed up line item entry</p>
              <Button onClick={() => setDialogOpen(true)}>
                <Plus className="w-4 h-4 mr-2" />
                Add First Product
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-slate-800">
                  <TableHead className="text-slate-400">Product</TableHead>
                  <TableHead className="text-slate-400">HS Code</TableHead>
                  <TableHead className="text-slate-400">Unit</TableHead>
                  <TableHead className="text-slate-400 text-right">Price</TableHead>
                  <TableHead className="text-slate-400">Origin</TableHead>
                  <TableHead className="text-slate-400">Uses</TableHead>
                  <TableHead className="text-slate-400 w-[100px]">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product) => (
                  <TableRow key={product.id} className="border-slate-800 hover:bg-slate-800/50">
                    <TableCell className="text-white">
                      <div className="flex items-start gap-2">
                        <Package className="w-4 h-4 text-slate-400 mt-1 flex-shrink-0" />
                        <div>
                          <div className="font-medium">{product.name}</div>
                          {product.sku && (
                            <span className="text-xs text-slate-400">SKU: {product.sku}</span>
                          )}
                          {product.short_description && (
                            <p className="text-xs text-slate-400 mt-1">{product.short_description}</p>
                          )}
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      {product.hs_code ? (
                        <Badge variant="outline" className="font-mono">
                          <Tag className="w-3 h-3 mr-1" />
                          {product.hs_code}
                        </Badge>
                      ) : (
                        <span className="text-slate-500">-</span>
                      )}
                    </TableCell>
                    <TableCell className="text-slate-300">{product.default_unit}</TableCell>
                    <TableCell className="text-slate-300 text-right">
                      {product.default_unit_price 
                        ? `${product.currency} ${product.default_unit_price.toLocaleString(undefined, { minimumFractionDigits: 2 })}`
                        : "-"
                      }
                    </TableCell>
                    <TableCell className="text-slate-300">{product.country_of_origin || "-"}</TableCell>
                    <TableCell className="text-slate-300">{product.use_count}</TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEdit(product)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(product.id)}
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
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingId ? "Edit Product" : "Add Product"}</DialogTitle>
            <DialogDescription>
              Add product details for quick line item entry
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>SKU</Label>
                <Input
                  value={form.sku}
                  onChange={(e) => setForm({ ...form, sku: e.target.value })}
                  placeholder="PROD-001"
                />
              </div>
              <div className="space-y-2 col-span-2">
                <Label>Product Name *</Label>
                <Input
                  value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="Cotton T-Shirts"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>HS Code</Label>
                <Input
                  value={form.hs_code}
                  onChange={(e) => setForm({ ...form, hs_code: e.target.value })}
                  placeholder="6109.10.00"
                />
              </div>
              <div className="space-y-2">
                <Label>Country of Origin</Label>
                <Input
                  value={form.country_of_origin}
                  onChange={(e) => setForm({ ...form, country_of_origin: e.target.value })}
                  placeholder="Bangladesh"
                />
              </div>
            </div>

            <div className="space-y-2">
              <Label>Full Description (for documents) *</Label>
              <Textarea
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="100% Cotton T-Shirts, Round Neck, Short Sleeve, Assorted Colors and Sizes..."
                rows={3}
              />
            </div>

            <div className="space-y-2">
              <Label>Short Description (for dropdown)</Label>
              <Input
                value={form.short_description}
                onChange={(e) => setForm({ ...form, short_description: e.target.value })}
                placeholder="Cotton T-Shirts, Assorted"
              />
            </div>

            <div className="grid grid-cols-4 gap-4">
              <div className="space-y-2">
                <Label>Unit Price</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={form.default_unit_price}
                  onChange={(e) => setForm({ ...form, default_unit_price: e.target.value })}
                  placeholder="5.50"
                />
              </div>
              <div className="space-y-2">
                <Label>Currency</Label>
                <Select value={form.currency} onValueChange={(v) => setForm({ ...form, currency: v })}>
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
                <Label>Default Unit</Label>
                <Select value={form.default_unit} onValueChange={(v) => setForm({ ...form, default_unit: v })}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {UNIT_OPTIONS.map((unit) => (
                      <SelectItem key={unit} value={unit}>{unit}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Units/Carton</Label>
                <Input
                  type="number"
                  value={form.units_per_carton}
                  onChange={(e) => setForm({ ...form, units_per_carton: e.target.value })}
                  placeholder="50"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-2">
                <Label>Weight per Unit (KG)</Label>
                <Input
                  type="number"
                  step="0.001"
                  value={form.weight_per_unit_kg}
                  onChange={(e) => setForm({ ...form, weight_per_unit_kg: e.target.value })}
                  placeholder="0.150"
                />
              </div>
              <div className="space-y-2">
                <Label>Carton Weight (KG)</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={form.carton_weight_kg}
                  onChange={(e) => setForm({ ...form, carton_weight_kg: e.target.value })}
                  placeholder="8.5"
                />
              </div>
              <div className="space-y-2">
                <Label>Carton Dimensions</Label>
                <Input
                  value={form.carton_dimensions}
                  onChange={(e) => setForm({ ...form, carton_dimensions: e.target.value })}
                  placeholder="60x40x30 cm"
                />
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>Cancel</Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
              {editingId ? "Update" : "Add Product"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default ProductCatalogPage;

