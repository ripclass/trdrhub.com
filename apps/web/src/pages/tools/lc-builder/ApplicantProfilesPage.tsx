/**
 * Applicant Profiles Page
 * 
 * Manage saved applicant (buyer/importer) profiles for quick LC creation.
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
  DialogTrigger,
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
  Building2,
  MoreVertical,
  Edit,
  Trash2,
  Globe,
  Phone,
  Mail,
  MapPin,
  FileText,
  Star,
  StarOff,
} from "lucide-react";

interface ApplicantProfile {
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
  bank_address: string;
  is_favorite: boolean;
  created_at: string;
  usage_count: number;
}

const emptyProfile: Omit<ApplicantProfile, "id" | "created_at" | "usage_count"> = {
  company_name: "",
  address: "",
  city: "",
  country: "",
  contact_person: "",
  email: "",
  phone: "",
  bank_name: "",
  bank_swift: "",
  bank_address: "",
  is_favorite: false,
};

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

export default function ApplicantProfilesPage() {
  const { session } = useAuth();
  const { toast } = useToast();
  
  const [profiles, setProfiles] = useState<ApplicantProfile[]>([]);
  const [filteredProfiles, setFilteredProfiles] = useState<ApplicantProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingProfile, setEditingProfile] = useState<ApplicantProfile | null>(null);
  const [formData, setFormData] = useState(emptyProfile);

  // Fetch profiles from API
  useEffect(() => {
    fetchProfiles();
  }, [session?.access_token]);

  const fetchProfiles = async () => {
    if (!session?.access_token) {
      setLoading(false);
      return;
    }
    
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/lc-builder/profiles/applicants`, {
        headers: {
          "Authorization": `Bearer ${session.access_token}`,
        },
      });
      
      if (res.ok) {
        const data = await res.json();
        setProfiles(data.profiles || []);
      }
    } catch (error) {
      console.error("Error fetching profiles:", error);
    } finally {
      setLoading(false);
    }
  };

  // Demo data fallback - shown when no API data
  useEffect(() => {
    if (!loading && profiles.length === 0 && !session?.access_token) {
      setProfiles([
        {
        id: "ap-1",
        company_name: "ABC Trading Co. Ltd",
        address: "123 Commerce Street, Suite 500",
        city: "New York",
        country: "United States",
        contact_person: "John Smith",
        email: "john@abctrading.com",
        phone: "+1 212 555 0123",
        bank_name: "Citibank N.A.",
        bank_swift: "CITIUS33",
        bank_address: "388 Greenwich Street, New York, NY 10013",
        is_favorite: true,
        created_at: "2024-01-15",
        usage_count: 25,
      },
      {
        id: "ap-2",
        company_name: "Euro Imports GmbH",
        address: "Industriestraße 45",
        city: "Frankfurt",
        country: "Germany",
        contact_person: "Hans Mueller",
        email: "hans@euroimports.de",
        phone: "+49 69 555 0456",
        bank_name: "Deutsche Bank AG",
        bank_swift: "DEUTDEFF",
        bank_address: "Taunusanlage 12, 60325 Frankfurt",
        is_favorite: false,
        created_at: "2024-02-20",
        usage_count: 12,
      },
      ]);
    }
  }, [loading, profiles.length, session?.access_token]);

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
          p.city.toLowerCase().includes(query)
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

  const openEditDialog = (profile: ApplicantProfile) => {
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
      bank_address: profile.bank_address,
      is_favorite: profile.is_favorite,
    });
    setIsDialogOpen(true);
  };

  const handleSave = async () => {
    if (!formData.company_name || !formData.country) {
      toast({
        title: "Validation Error",
        description: "Company name and country are required",
        variant: "destructive",
      });
      return;
    }

    if (!session?.access_token) {
      // Offline mode - local state only
      if (editingProfile) {
        setProfiles(profiles.map(p => 
          p.id === editingProfile.id ? { ...p, ...formData } : p
        ));
      } else {
        const newProfile: ApplicantProfile = {
          id: `ap-${Date.now()}`,
          ...formData,
          created_at: new Date().toISOString().split("T")[0],
          usage_count: 0,
        };
        setProfiles([...profiles, newProfile]);
      }
      setIsDialogOpen(false);
      return;
    }

    try {
      const url = editingProfile
        ? `${API_BASE}/lc-builder/profiles/applicants/${editingProfile.id}`
        : `${API_BASE}/lc-builder/profiles/applicants`;
      
      const res = await fetch(url, {
        method: editingProfile ? "PUT" : "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`,
        },
        body: JSON.stringify(formData),
      });

      if (res.ok) {
        toast({
          title: editingProfile ? "Profile Updated" : "Profile Created",
          description: `${formData.company_name} has been ${editingProfile ? "updated" : "added"}`,
        });
        fetchProfiles();
        setIsDialogOpen(false);
      } else {
        throw new Error("Failed to save");
      }
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to save profile",
        variant: "destructive",
      });
    }
  };

  const handleSaveOld = () => {
    if (!formData.company_name || !formData.country) {
      toast({
        title: "Validation Error",
        description: "Company name and country are required",
        variant: "destructive",
      });
      return;
    }

    if (editingProfile) {
      // Update existing
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
      // Create new
      const newProfile: ApplicantProfile = {
        id: `ap-${Date.now()}`,
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

  const handleDelete = async (id: string) => {
    if (session?.access_token) {
      try {
        const res = await fetch(`${API_BASE}/lc-builder/profiles/applicants/${id}`, {
          method: "DELETE",
          headers: {
            "Authorization": `Bearer ${session.access_token}`,
          },
        });
        
        if (res.ok) {
          toast({
            title: "Profile Deleted",
            description: "Applicant profile has been removed",
          });
          fetchProfiles();
        }
      } catch (error) {
        toast({
          title: "Error",
          description: "Failed to delete profile",
          variant: "destructive",
        });
      }
    } else {
      setProfiles(profiles.filter(p => p.id !== id));
      toast({
        title: "Profile Deleted",
        description: "Applicant profile has been removed",
      });
    }
  };

  const toggleFavorite = async (id: string) => {
    const profile = profiles.find(p => p.id === id);
    if (!profile) return;
    
    if (session?.access_token) {
      try {
        await fetch(`${API_BASE}/lc-builder/profiles/applicants/${id}`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${session.access_token}`,
          },
          body: JSON.stringify({ ...profile, is_favorite: !profile.is_favorite }),
        });
        fetchProfiles();
      } catch (error) {
        console.error("Failed to update favorite:", error);
      }
    } else {
      setProfiles(profiles.map(p => 
        p.id === id ? { ...p, is_favorite: !p.is_favorite } : p
      ));
    }
  };

  return (
    <div className="min-h-screen bg-slate-950">
      {/* Header */}
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-bold text-white flex items-center gap-2">
                <Building2 className="h-5 w-5 text-emerald-400" />
                Applicant Profiles
              </h1>
              <p className="text-sm text-slate-400">
                Saved buyer/importer profiles for quick LC creation
              </p>
            </div>
            <Button
              className="bg-emerald-600 hover:bg-emerald-700"
              onClick={openCreateDialog}
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Applicant
            </Button>
          </div>
        </div>
      </div>

      {/* Search */}
      <div className="px-6 py-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search applicants..."
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
            <Building2 className="h-12 w-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-white mb-2">No applicant profiles</h3>
            <p className="text-slate-400 mb-4">Add your first buyer/importer profile</p>
            <Button onClick={openCreateDialog}>
              <Plus className="h-4 w-4 mr-2" />
              Add Applicant
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredProfiles.map((profile) => (
              <Card
                key={profile.id}
                className="bg-slate-800/50 border-slate-700"
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2">
                      <div className="p-2 rounded-lg bg-blue-500/10">
                        <Building2 className="h-5 w-5 text-blue-400" />
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
                  {profile.contact_person && (
                    <div className="flex items-center gap-2 text-sm text-slate-300">
                      <FileText className="h-4 w-4 text-slate-500" />
                      {profile.contact_person}
                    </div>
                  )}
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
            ))}
          </div>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingProfile ? "Edit Applicant Profile" : "Add Applicant Profile"}
            </DialogTitle>
            <DialogDescription>
              Save buyer/importer details for quick LC creation
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
                    placeholder="ABC Trading Co. Ltd"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Contact Person</Label>
                  <Input
                    value={formData.contact_person}
                    onChange={(e) => setFormData({ ...formData, contact_person: e.target.value })}
                    placeholder="John Smith"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Address</Label>
                <Textarea
                  value={formData.address}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="123 Commerce Street, Suite 500"
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
                    placeholder="New York"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Country *</Label>
                  <Input
                    value={formData.country}
                    onChange={(e) => setFormData({ ...formData, country: e.target.value })}
                    placeholder="United States"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
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
                <div className="space-y-2">
                  <Label>Phone</Label>
                  <Input
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    placeholder="+1 212 555 0123"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
            </div>

            {/* Bank Details */}
            <div className="space-y-4 pt-4 border-t border-slate-700">
              <h3 className="text-sm font-medium text-slate-400">Issuing Bank Details</h3>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  <Label>Bank Name</Label>
                  <Input
                    value={formData.bank_name}
                    onChange={(e) => setFormData({ ...formData, bank_name: e.target.value })}
                    placeholder="Citibank N.A."
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label>SWIFT Code</Label>
                  <Input
                    value={formData.bank_swift}
                    onChange={(e) => setFormData({ ...formData, bank_swift: e.target.value })}
                    placeholder="CITIUS33"
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Bank Address</Label>
                <Input
                  value={formData.bank_address}
                  onChange={(e) => setFormData({ ...formData, bank_address: e.target.value })}
                  placeholder="388 Greenwich Street, New York, NY 10013"
                  className="bg-slate-800 border-slate-700"
                />
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

