import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import {
  Landmark,
  Plus,
  Users,
  Mail,
  Building2,
  Globe,
  Shield,
  UserPlus,
  Eye,
  Copy,
  Check,
  AlertCircle,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/hooks/use-toast";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Alert,
  AlertDescription,
  AlertTitle,
} from "@/components/ui/alert";

const API_BASE = import.meta.env.VITE_API_URL || "https://trdrhub-api.onrender.com";

interface Bank {
  id: string;
  name: string;
  legal_name: string | null;
  type: string;
  country: string | null;
  contact_email: string | null;
  regulator_id: string | null;
  status: string;
  created_at: string;
  user_count: number;
}

interface BankUser {
  id: string;
  email: string;
  name: string;
  role: string;
  status: string;
  joined_at: string | null;
}

interface BankDetail extends Bank {
  users: BankUser[];
  pending_invitations: Array<{
    id: string;
    email: string;
    role: string;
    expires_at: string | null;
  }>;
}

interface CreateBankForm {
  bank_name: string;
  legal_name: string;
  country: string;
  contact_email: string;
  contact_name: string;
  regulator_id: string;
  owner_email: string;
  owner_name: string;
}

interface InviteUserForm {
  email: string;
  name: string;
  role: string;
}

interface CredentialsInfo {
  email: string;
  password: string;
  bankName: string;
}

export function BankManagement() {
  const { toast } = useToast();
  const [banks, setBanks] = useState<Bank[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Dialog states
  const [createOpen, setCreateOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [inviteOpen, setInviteOpen] = useState(false);
  const [credentialsOpen, setCredentialsOpen] = useState(false);
  
  // Selected bank for detail/invite
  const [selectedBank, setSelectedBank] = useState<BankDetail | null>(null);
  const [selectedBankId, setSelectedBankId] = useState<string | null>(null);
  
  // Form states
  const [createForm, setCreateForm] = useState<CreateBankForm>({
    bank_name: "",
    legal_name: "",
    country: "",
    contact_email: "",
    contact_name: "",
    regulator_id: "",
    owner_email: "",
    owner_name: "",
  });
  
  const [inviteForm, setInviteForm] = useState<InviteUserForm>({
    email: "",
    name: "",
    role: "bank_officer",
  });
  
  // Credentials display
  const [credentials, setCredentials] = useState<CredentialsInfo | null>(null);
  const [copied, setCopied] = useState(false);
  
  const [submitting, setSubmitting] = useState(false);

  // Fetch banks
  const loadBanks = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/admin/banks`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load banks");
      const data = await res.json();
      setBanks(data);
      setError(null);
    } catch (err) {
      console.error(err);
      setError("Unable to load banks. You may not have admin permissions.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadBanks();
  }, [loadBanks]);

  // Fetch bank detail
  const loadBankDetail = async (bankId: string) => {
    try {
      const res = await fetch(`${API_BASE}/admin/banks/${bankId}`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error("Failed to load bank details");
      const data = await res.json();
      setSelectedBank(data);
      setDetailOpen(true);
    } catch (err) {
      console.error(err);
      toast({
        title: "Error",
        description: "Failed to load bank details",
        variant: "destructive",
      });
    }
  };

  // Create bank
  const handleCreateBank = async () => {
    if (!createForm.bank_name || !createForm.owner_email || !createForm.owner_name) {
      toast({
        title: "Missing fields",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/admin/banks`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createForm),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create bank");
      }
      
      toast({
        title: "Bank created",
        description: `${createForm.bank_name} has been created successfully`,
      });
      
      // Show credentials
      if (data.temp_password) {
        setCredentials({
          email: createForm.owner_email,
          password: data.temp_password,
          bankName: createForm.bank_name,
        });
        setCredentialsOpen(true);
      }
      
      setCreateOpen(false);
      setCreateForm({
        bank_name: "",
        legal_name: "",
        country: "",
        contact_email: "",
        contact_name: "",
        regulator_id: "",
        owner_email: "",
        owner_name: "",
      });
      loadBanks();
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Failed to create bank",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Invite user to bank
  const handleInviteUser = async () => {
    if (!selectedBankId || !inviteForm.email || !inviteForm.name) {
      toast({
        title: "Missing fields",
        description: "Please fill in all required fields",
        variant: "destructive",
      });
      return;
    }
    
    setSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/admin/banks/${selectedBankId}/invite`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(inviteForm),
      });
      
      const data = await res.json();
      
      if (!res.ok) {
        throw new Error(data.detail || "Failed to invite user");
      }
      
      toast({
        title: "User invited",
        description: `${inviteForm.email} has been added`,
      });
      
      // Show credentials
      if (data.temp_password) {
        setCredentials({
          email: inviteForm.email,
          password: data.temp_password,
          bankName: selectedBank?.name || "Bank",
        });
        setCredentialsOpen(true);
      }
      
      setInviteOpen(false);
      setInviteForm({ email: "", name: "", role: "bank_officer" });
      
      // Refresh bank detail if open
      if (selectedBankId) {
        loadBankDetail(selectedBankId);
      }
      loadBanks();
    } catch (err: any) {
      toast({
        title: "Error",
        description: err.message || "Failed to invite user",
        variant: "destructive",
      });
    } finally {
      setSubmitting(false);
    }
  };

  // Copy credentials to clipboard
  const copyCredentials = () => {
    if (!credentials) return;
    const text = `Bank: ${credentials.bankName}\nEmail: ${credentials.email}\nTemporary Password: ${credentials.password}\n\nPlease change your password after first login at: https://trdrhub.com/login`;
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Landmark className="h-6 w-6 text-primary" />
            Bank Management
          </h2>
          <p className="text-muted-foreground">
            Create and manage bank accounts. Banks are invite-only.
          </p>
        </div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Add Bank
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Create New Bank</DialogTitle>
              <DialogDescription>
                Set up a new bank account. This will create the company and owner account.
              </DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="bank_name">Bank Name *</Label>
                  <Input
                    id="bank_name"
                    placeholder="First National Bank"
                    value={createForm.bank_name}
                    onChange={(e) => setCreateForm({ ...createForm, bank_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="legal_name">Legal Name</Label>
                  <Input
                    id="legal_name"
                    placeholder="First National Bank Ltd."
                    value={createForm.legal_name}
                    onChange={(e) => setCreateForm({ ...createForm, legal_name: e.target.value })}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="country">Country *</Label>
                  <Input
                    id="country"
                    placeholder="Bangladesh"
                    value={createForm.country}
                    onChange={(e) => setCreateForm({ ...createForm, country: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="regulator_id">Regulator ID</Label>
                  <Input
                    id="regulator_id"
                    placeholder="SWIFT/BIC code or license number"
                    value={createForm.regulator_id}
                    onChange={(e) => setCreateForm({ ...createForm, regulator_id: e.target.value })}
                  />
                </div>
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="contact_name">Contact Person *</Label>
                  <Input
                    id="contact_name"
                    placeholder="John Smith"
                    value={createForm.contact_name}
                    onChange={(e) => setCreateForm({ ...createForm, contact_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="contact_email">Contact Email *</Label>
                  <Input
                    id="contact_email"
                    type="email"
                    placeholder="contact@bank.com"
                    value={createForm.contact_email}
                    onChange={(e) => setCreateForm({ ...createForm, contact_email: e.target.value })}
                  />
                </div>
              </div>
              
              <div className="border-t pt-4 mt-2">
                <h4 className="text-sm font-medium mb-3">Owner Account</h4>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="owner_name">Owner Name *</Label>
                    <Input
                      id="owner_name"
                      placeholder="Admin User"
                      value={createForm.owner_name}
                      onChange={(e) => setCreateForm({ ...createForm, owner_name: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="owner_email">Owner Email *</Label>
                    <Input
                      id="owner_email"
                      type="email"
                      placeholder="admin@bank.com"
                      value={createForm.owner_email}
                      onChange={(e) => setCreateForm({ ...createForm, owner_email: e.target.value })}
                    />
                  </div>
                </div>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setCreateOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleCreateBank} disabled={submitting}>
                {submitting ? "Creating..." : "Create Bank"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Error</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Banks List */}
      <Card>
        <CardHeader>
          <CardTitle>Registered Banks</CardTitle>
          <CardDescription>
            {banks.length} bank{banks.length !== 1 ? "s" : ""} registered on the platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <Skeleton key={i} className="h-16 w-full" />
              ))}
            </div>
          ) : banks.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <Landmark className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p>No banks registered yet</p>
              <p className="text-sm">Click "Add Bank" to create the first one</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Bank</TableHead>
                  <TableHead>Country</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {banks.map((bank) => (
                  <TableRow key={bank.id}>
                    <TableCell>
                      <div className="flex items-center gap-3">
                        <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                          <Landmark className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <p className="font-medium">{bank.name}</p>
                          <p className="text-xs text-muted-foreground">{bank.contact_email}</p>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <Globe className="h-4 w-4 text-muted-foreground" />
                        {bank.country || "—"}
                      </div>
                    </TableCell>
                    <TableCell>
                      <div className="flex items-center gap-1.5">
                        <Users className="h-4 w-4 text-muted-foreground" />
                        {bank.user_count}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={bank.status === "active" ? "default" : "secondary"}>
                        {bank.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(bank.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-2">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => loadBankDetail(bank.id)}
                        >
                          <Eye className="h-4 w-4 mr-1" />
                          View
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            setSelectedBankId(bank.id);
                            setSelectedBank({ ...bank, users: [], pending_invitations: [] } as BankDetail);
                            setInviteOpen(true);
                          }}
                        >
                          <UserPlus className="h-4 w-4 mr-1" />
                          Add User
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

      {/* Bank Detail Dialog */}
      <Dialog open={detailOpen} onOpenChange={setDetailOpen}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Landmark className="h-5 w-5" />
              {selectedBank?.name}
            </DialogTitle>
            <DialogDescription>
              Bank details and user management
            </DialogDescription>
          </DialogHeader>
          {selectedBank && (
            <div className="space-y-6">
              {/* Bank Info */}
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground">Legal Name</p>
                  <p className="font-medium">{selectedBank.legal_name || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Country</p>
                  <p className="font-medium">{selectedBank.country || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Contact Email</p>
                  <p className="font-medium">{selectedBank.contact_email || "—"}</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Regulator ID</p>
                  <p className="font-medium">{selectedBank.regulator_id || "—"}</p>
                </div>
              </div>
              
              {/* Users */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-medium">Users ({selectedBank.users.length})</h4>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedBankId(selectedBank.id);
                      setInviteOpen(true);
                    }}
                  >
                    <UserPlus className="h-4 w-4 mr-1" />
                    Add User
                  </Button>
                </div>
                {selectedBank.users.length === 0 ? (
                  <p className="text-sm text-muted-foreground">No users yet</p>
                ) : (
                  <div className="border rounded-lg divide-y">
                    {selectedBank.users.map((user) => (
                      <div key={user.id} className="p-3 flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-primary/10 flex items-center justify-center text-sm font-medium">
                            {user.name.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium text-sm">{user.name}</p>
                            <p className="text-xs text-muted-foreground">{user.email}</p>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">{user.role.replace("_", " ")}</Badge>
                          <Badge variant={user.status === "active" ? "default" : "secondary"}>
                            {user.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {/* Pending Invitations */}
              {selectedBank.pending_invitations.length > 0 && (
                <div>
                  <h4 className="font-medium mb-3">Pending Invitations</h4>
                  <div className="border rounded-lg divide-y">
                    {selectedBank.pending_invitations.map((inv) => (
                      <div key={inv.id} className="p-3 flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{inv.email}</p>
                          <p className="text-xs text-muted-foreground">
                            Expires: {inv.expires_at ? new Date(inv.expires_at).toLocaleDateString() : "—"}
                          </p>
                        </div>
                        <Badge variant="secondary">{inv.role}</Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Invite User Dialog */}
      <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add User to {selectedBank?.name || "Bank"}</DialogTitle>
            <DialogDescription>
              Create a new user account for this bank
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="invite_name">Full Name *</Label>
              <Input
                id="invite_name"
                placeholder="John Smith"
                value={inviteForm.name}
                onChange={(e) => setInviteForm({ ...inviteForm, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite_email">Email *</Label>
              <Input
                id="invite_email"
                type="email"
                placeholder="john@bank.com"
                value={inviteForm.email}
                onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="invite_role">Role</Label>
              <Select
                value={inviteForm.role}
                onValueChange={(value) => setInviteForm({ ...inviteForm, role: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="bank_admin">
                    <div className="flex items-center gap-2">
                      <Shield className="h-4 w-4" />
                      Bank Admin
                    </div>
                  </SelectItem>
                  <SelectItem value="bank_officer">
                    <div className="flex items-center gap-2">
                      <Users className="h-4 w-4" />
                      Bank Officer
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                Admins can manage users and settings. Officers can process LCs.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setInviteOpen(false)}>
              Cancel
            </Button>
            <Button onClick={handleInviteUser} disabled={submitting}>
              {submitting ? "Adding..." : "Add User"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Credentials Dialog */}
      <Dialog open={credentialsOpen} onOpenChange={setCredentialsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-green-600">
              <Check className="h-5 w-5" />
              Account Created Successfully
            </DialogTitle>
            <DialogDescription>
              Share these credentials securely with the user
            </DialogDescription>
          </DialogHeader>
          {credentials && (
            <div className="space-y-4 py-4">
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>Important</AlertTitle>
                <AlertDescription>
                  This is the only time you'll see this password. Make sure to copy it now.
                </AlertDescription>
              </Alert>
              
              <div className="rounded-lg border bg-muted/50 p-4 space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Bank</p>
                  <p className="font-medium">{credentials.bankName}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Email</p>
                  <p className="font-mono text-sm">{credentials.email}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground mb-1">Temporary Password</p>
                  <p className="font-mono text-sm bg-yellow-100 dark:bg-yellow-900/30 px-2 py-1 rounded">
                    {credentials.password}
                  </p>
                </div>
              </div>
              
              <Button onClick={copyCredentials} className="w-full gap-2">
                {copied ? (
                  <>
                    <Check className="h-4 w-4" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="h-4 w-4" />
                    Copy Credentials
                  </>
                )}
              </Button>
              
              <p className="text-xs text-muted-foreground text-center">
                The user should change their password after first login
              </p>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setCredentialsOpen(false)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default BankManagement;

