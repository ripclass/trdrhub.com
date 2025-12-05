/**
 * Beneficiary Directory Page
 * 
 * Manage saved beneficiary (seller/exporter) profiles for quick LC creation.
 */

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useToast } from "@/hooks/use-toast";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Search,
  Plus,
  Users,
  MoreVertical,
  Edit,
  Trash2,
  Globe,
  Mail,
  Building2,
  Star,
  StarOff,
  Shirt,
  Cpu,
  Package,
} from "lucide-react";

interface BeneficiaryProfile {
  id: string;
  company_name: string;
  address: string;
  city: string;
  country: string;
  contact_person: string;
  email: string;
  phone: string;
  bank_name: string;
  bank_swift: string;
  bank_account: string;
  bank_address: string;
  industry: string;
  is_favorite: boolean;
  created_at: string;
  usage_count: number;
}

const emptyProfile: Omit<BeneficiaryProfile, "id" | "created_at" | "usage_count"> = {
  company_name: "",
  address: "",
  city: "",
  country: "",
  contact_person: "",
  email: "",
  phone: "",
  bank_name: "",
  bank_swift: "",
  bank_account: "",
  bank_address: "",
  industry: "general",
  is_favorite: false,
};

const industryOptions = [
  { value: "textiles", label: "Textiles/RMG", icon: Shirt },
  { value: "electronics", label: "Electronics", icon: Cpu },
  { value: "general", label: "General Trading", icon: Package },
];

export default function BeneficiaryDirectoryPage() {
  const { session } = useAuth();
  const { toast } = useToast();
  
  const [profiles, setProfiles] = useState<BeneficiaryProfile[]>([]);
  const [filteredProfiles, setFilteredProfiles] = useState<BeneficiaryProfile[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<BeneficiaryProfile | null>(null);
  const [formData, setFormData] = useState(emptyProfile);

  // Demo data
  useEffect(() => {
    setProfiles([
      {
        id: "bp-1",
        company_name: "Fashion Garments Ltd",
        address: "Plot 123, BSCIC Industrial Area",
        city: "Dhaka",
        country: "Bangladesh",
        contact_person: "Mohammad Rahman",
        email: "rahman@fashiongarments.bd",
        phone: "+880 2 8901234",
        bank_name: "Standard Chartered Bank Bangladesh",
        bank_swift: "SCBLBDDX",
        bank_account: "0123456789012",
        bank_address: "67 Gulshan Avenue, Dhaka 1212",
        industry: "textiles",
        is_favorite: true,
        created_at: "2024-01-10",
        usage_count: 45,
      },
      {
        id: "bp-2",
        company_name: "Shenzhen Electronics Co. Ltd",
        address: "Building A, Tech Park, Nanshan District",
        city: "Shenzhen",
        country: "China",
        contact_person: "Wang Lei",
        email: "wang@szelectronics.cn",
        phone: "+86 755 8888 9999",
        bank_name: "Bank of China",
        bank_swift: "BKCHCNBJ",
        bank_account: "6212261234567890",
        bank_address: "1 Fuxingmen Nei Dajie, Beijing",
        industry: "electronics",
        is_favorite: false,
        created_at: "2024-02-15",
        usage_count: 18,
      },
      {
        id: "bp-3",
        company_name: "Karachi Exports Pvt Ltd",
        address: "Suite 501, Trade Tower",
        city: "Karachi",
        country: "Pakistan",
        contact_person: "Ali Hassan",
        email: "ali@karachiexports.pk",
        phone: "+92 21 3456 7890",
        bank_name: "Habib Bank Limited",
        bank_swift: "HABORPKA",
        bank_account: "0102345678901",
        bank_address: "Habib Bank Plaza, Karachi",
        industry: "textiles",
        is_favorite: false,
        created_at: "2024-03-01",
        usage_count: 12,
      },
    ]);
  }, []);

  useEffect(() => {
    filterProfiles();
  }, [profiles, searchQuery]);

  const filterProfiles = () => {
    let filtered = [...profiles];
    
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.company_name.toLowerCase().includes(query) ||
          p.country.toLowerCase().includes(query) ||
          p.city.toLowerCase().includes(query) ||
          p.industry.toLowerCase().includes(query)
      );
    }
    
    // Sort: favorites first, then by usage
    filtered.sort((a, b) => {
      if (a.is_favorite !== b.is_favorite) return a.is_favorite ? -1 : 1;
      return b.usage_count - a.usage_count;
    });
    
    setFilteredProfiles(filtered);
  };

  const openCreateDialog = () => {
    setEditingProfile(null);
    setFormData(emptyProfile);
    setIsDialogOpen(true);
  };

  const openEditDialog = (profile: BeneficiaryProfile) => {
    setEditingProfile(profile);
    setFormData({
      company_name: profile.company_name,
      address: profile.address,
      city: profile.city,
      country: profile.country,
      contact_person: profile.contact_person,
      email: profile.email,
      phone: profile.phone,
      bank_name: profile.bank_name,
      bank_swift: profile.bank_swift,
      bank_account: profile.bank_account,
      bank_address: profile.bank_address,
      industry: profile.industry,
      is_favorite: profile.is_favorite,
    });
    setIsDialogOpen(true);
  };

  const handleSave = () => {
    if (!formData.company_name || !formData.country) {
      toast({
        title: "Validation Error",
        description: "Company name and country are required",
        variant: "destructive",
      });
      return;
    }

    if (editingProfile) {
      setProfiles(profiles.map(p => 
        p.id === editingProfile.id 
          ? { ...p, ...formData }
          : p
      ));
      toast({
        title: "Profile Updated",
        description: `${formData.company_name} has been updated`,
      });
    } else {
      const newProfile: BeneficiaryProfile = {
        id: `bp-${Date.now()}`,
        ...formData,
        created_at: new Date().toISOString().split("T")[0],
        usage_count: 0,
      };
      setProfiles([...profiles, newProfile]);
      toast({
        title: "Profile Created",
        description: `${formData.company_name} has been added`,
      });
    }
    
    setIsDialogOpen(false);
  };

  const handleDelete = (id: string) => {
    setProfiles(profiles.filter(p => p.id !== id));
    toast({
      title: "Profile Deleted",
      description: "Beneficiary profile has been removed",
    });
  };

  const toggleFavorite = (id: string) => {
    setProfiles(profiles.map(p => 
      p.id === id ? { ...p, is_favorite: !p.is_favorite } : p
    ));
  };

  const getIndustryIcon = (industry: string) => {
    const found = industryOptions.find(i => i.value === industry);
    return found?.icon || Package;
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Users className="h-5 w-5 text-emerald-400" />
                Beneficiary Directory
              </h1>
              <p className="text-sm text-slate-400">
                Saved seller/exporter profiles for quick LC creation
              </p>
            </div>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={openCreateDialog}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Beneficiary
            </Button>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-6 py-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search beneficiaries..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 bg-slate-800 border-slate-700"
          />
        </div>
      </div>

      {/* Profiles Grid */}
      <div className="px-6 py-4">
        {filteredProfiles.length === 0 ? (
          <div className="text-center py-12">
            <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No beneficiary profiles</h3>
            <p className="text-slate-400 mb-4">Add your first seller/exporter profile</p>
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Add Beneficiary
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredProfiles.map((profile) => {
              const IndustryIcon = getIndustryIcon(profile.industry);
              
              return (
                <Card
                  key={profile.id}
                  className="bg-slate-800/50 border-slate-700"
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-2">
                        <div className="p-2 rounded-lg bg-emerald-500/10">
                          <IndustryIcon className="h-5 w-5 text-emerald-400" />
                        </div>
                        <button
                          onClick={() => toggleFavorite(profile.id)}
                          className="text-slate-400 hover:text-yellow-400 transition-colors"
                        >
                          {profile.is_favorite ? (
                            <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                          ) : (
                            <StarOff className="h-4 w-4" />
                          )}
                        </button>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => openEditDialog(profile)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-red-400"
                            onClick={() => handleDelete(profile.id)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <CardTitle className="text-lg text-white mt-2">
                      {profile.company_name}
                    </CardTitle>
                    <CardDescription className="text-slate-400 flex items-center gap-1">
                      <Globe className="h-3 w-3" />
                      {profile.city}, {profile.country}
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <Badge variant="outline" className="text-xs capitalize">
                      {profile.industry}
                    </Badge>
                    {profile.email && (
                      <div className="flex items-center gap-2 text-sm text-slate-300">
                        <Mail className="h-4 w-4 text-slate-500" />
                        {profile.email}
                      </div>
                    )}
                    {profile.bank_name && (
                      <div className="flex items-center gap-2 text-sm text-slate-300">
                        <Building2 className="h-4 w-4 text-slate-500" />
                        {profile.bank_name}
                        {profile.bank_swift && (
                          <Badge variant="outline" className="text-xs">
                            {profile.bank_swift}
                          </Badge>
                        )}
                      </div>
                    )}
                    <div className="pt-2 text-xs text-slate-500">
                      Used {profile.usage_count} times
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProfile ? "Edit Beneficiary Profile" : "Add Beneficiary Profile"}
            </DialogTitle>
            <DialogDescription>
              Save seller/exporter details for quick LC creation
            </DialogDescription>
          </DialogHeader>

          <div className="grid gap-4 py-4">
            {/* Company Details */}
            <div className="space-y-4">
              <h3 className="text-sm font-medium text-slate-400">Company Details</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Company Name *</Label>
                  <Input
                    value={formData.company_name}
                    onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
                    placeholder="Fashion Garments Ltd"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Industry</Label>
                  <select
                    value={formData.industry}
                    onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                    className="w-full h-10 px-3 rounded-md bg-slate-800 border border-slate-700 text-white"
                  >
                    {industryOptions.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="space-y-2">
                <Label>Address</Label>
                <Textarea
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Plot 123, Industrial Area"
                  className="bg-slate-800 border-slate-700"
                  rows={2}
                />
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>City</Label>
                  <Input
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="Dhaka"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Country *</Label>
                  <Input
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="Bangladesh"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Contact Person</Label>
                  <Input
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    placeholder="Mohammad Rahman"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Email</Label>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="contact@company.com"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
            </div>

            {/* Bank Details */}
            <div className="space-y-4 pt-4 border-t border-slate-700">
              <h3 className="text-sm font-medium text-slate-400">Advising/Negotiating Bank Details</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Bank Name</Label>
                  <Input
                    value={formData.bank_name}
                    onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                    placeholder="Standard Chartered Bank"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>SWIFT Code</Label>
                  <Input
                    value={formData.bank_swift}
                    onChange={(e) => setFormData({ ...formData, bank_swift: e.target.value })}
                    placeholder="SCBLBDDX"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Account Number</Label>
                  <Input
                    value={formData.bank_account}
                    onChange={(e) => setFormData({ ...formData, bank_account: e.target.value })}
                    placeholder="0123456789012"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Bank Address</Label>
                  <Input
                    value={formData.bank_address}
                    onChange={(e) => setFormData({ ...formData, bank_address: e.target.value })}
                    placeholder="67 Gulshan Avenue, Dhaka"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDialogOpen(false)}>
              Cancel
            </Button>
            <Button className="bg-emerald-600 hover:bg-emerald-700" onClick={handleSave}>
              {editingProfile ? "Update" : "Create"} Profile
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

