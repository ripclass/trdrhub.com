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
import { UserPlus, Shield, UserMinus, RotateCcw, KeyRound } from "lucide-react";
import { bankUsersApi, type BankUser, type BankUserInviteRequest, type RoleUpdateRequest } from "@/api/bank";
import { format } from "date-fns";

const PAGE_SIZE = 20;

export function BankUsersPage() {
  const { toast } = useToast();
  const { user } = useBankAuth();
  const isBankAdmin = user?.role === "bank_admin";
  
  // Early return if not admin - defense in depth
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
  
  const [users, setUsers] = React.useState<BankUser[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [page, setPage] = React.useState(1);
  const [total, setTotal] = React.useState(0);
  const [searchTerm, setSearchTerm] = React.useState("");
  const [roleFilter, setRoleFilter] = React.useState<"bank_officer" | "bank_admin" | "all">("all");
  const [statusFilter, setStatusFilter] = React.useState<boolean | "all">("all");
  const [actionId, setActionId] = React.useState<string | null>(null);
  
  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [inviteData, setInviteData] = React.useState<BankUserInviteRequest>({
    email: "",
    full_name: "",
    password: "",
    role: "bank_officer",
  });

  const loadUsers = React.useCallback(async () => {
    setLoading(true);
    try {
      const response = await bankUsersApi.listUsers({
        page,
        per_page: PAGE_SIZE,
        search: searchTerm || undefined,
        role: roleFilter !== "all" ? roleFilter : undefined,
        is_active: statusFilter !== "all" ? statusFilter : undefined,
        sort_by: "created_at",
        sort_order: "desc",
      });
      setUsers(response.users);
      setTotal(response.total);
    } catch (error) {
      console.error("Failed to load users", error);
      toast({
        title: "Error",
        description: "Failed to load users. Please try again.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [page, searchTerm, roleFilter, statusFilter, toast]);

  React.useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleInvite = async () => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can invite users",
        variant: "destructive",
      });
      return;
    }
    if (!inviteData.email || !inviteData.full_name || !inviteData.password) {
      toast({
        title: "Validation Error",
        description: "Please fill in all fields",
        variant: "destructive",
      });
      return;
    }
    
    setActionId("invite");
    try {
      await bankUsersApi.inviteUser(inviteData);
      toast({
        title: "Success",
        description: `User ${inviteData.email} has been invited`,
      });
      setInviteOpen(false);
      setInviteData({ email: "", full_name: "", password: "", role: "bank_officer" });
      loadUsers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to invite user",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleRoleChange = async (userId: string, newRole: "bank_officer" | "bank_admin") => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can change user roles",
        variant: "destructive",
      });
      return;
    }
    setActionId(userId);
    try {
      const data: RoleUpdateRequest = {
        user_id: userId,
        role: newRole,
        reason: "Role change by bank admin",
      };
      await bankUsersApi.updateUserRole(userId, data);
      toast({
        title: "Success",
        description: "User role updated",
      });
      loadUsers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update role",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleSuspend = async (userId: string) => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can suspend users",
        variant: "destructive",
      });
      return;
    }
    setActionId(userId);
    try {
      await bankUsersApi.suspendUser(userId);
      toast({
        title: "Success",
        description: "User suspended",
      });
      loadUsers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to suspend user",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleReactivate = async (userId: string) => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can reactivate users",
        variant: "destructive",
      });
      return;
    }
    setActionId(userId);
    try {
      await bankUsersApi.reactivateUser(userId);
      toast({
        title: "Success",
        description: "User reactivated",
      });
      loadUsers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to reactivate user",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const handleReset2FA = async (userId: string) => {
    if (!isBankAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only bank admins can reset 2FA",
        variant: "destructive",
      });
      return;
    }
    setActionId(userId);
    try {
      await bankUsersApi.reset2FA(userId);
      toast({
        title: "Success",
        description: "2FA reset requested. User will receive instructions via email.",
      });
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to reset 2FA",
        variant: "destructive",
      });
    } finally {
      setActionId(null);
    }
  };

  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-semibold">Bank Users</h2>
          <p className="text-sm text-muted-foreground">
            Manage users in your bank tenant
          </p>
        </div>
        {isBankAdmin && (
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="w-4 h-4 mr-2" />
                Invite User
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite Bank User</DialogTitle>
              <DialogDescription>
                Create a new user account for your bank tenant
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invite-email">Email</Label>
                <Input
                  id="invite-email"
                  type="email"
                  placeholder="user@bank.com"
                  value={inviteData.email}
                  onChange={(e) => setInviteData({ ...inviteData, email: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-name">Full Name</Label>
                <Input
                  id="invite-name"
                  placeholder="John Doe"
                  value={inviteData.full_name}
                  onChange={(e) => setInviteData({ ...inviteData, full_name: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-password">Password</Label>
                <Input
                  id="invite-password"
                  type="password"
                  placeholder="Minimum 8 characters"
                  value={inviteData.password}
                  onChange={(e) => setInviteData({ ...inviteData, password: e.target.value })}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-role">Role</Label>
                <Select
                  value={inviteData.role}
                  onValueChange={(value: "bank_officer" | "bank_admin") =>
                    setInviteData({ ...inviteData, role: value })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="bank_officer">Bank Officer</SelectItem>
                    <SelectItem value="bank_admin">Bank Admin</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setInviteOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleInvite} disabled={actionId === "invite"}>
                {actionId === "invite" ? "Inviting..." : "Invite"}
              </Button>
            </DialogFooter>
          </DialogContent>
          </Dialog>
        )}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            Manage user accounts, roles, and access
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <div className="flex gap-4">
              <Input
                placeholder="Search by email or name..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="max-w-sm"
              />
              <Select value={roleFilter} onValueChange={(value: any) => setRoleFilter(value)}>
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="bank_officer">Bank Officer</SelectItem>
                  <SelectItem value="bank_admin">Bank Admin</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={statusFilter === "all" ? "all" : statusFilter ? "active" : "inactive"}
                onValueChange={(value) =>
                  setStatusFilter(value === "all" ? "all" : value === "active")
                }
              >
                <SelectTrigger className="w-[180px]">
                  <SelectValue placeholder="Filter by status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="active">Active</SelectItem>
                  <SelectItem value="inactive">Inactive</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">
                      Loading...
                    </TableCell>
                  </TableRow>
                ) : users.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={6} className="text-center">
                      No users found
                    </TableCell>
                  </TableRow>
                ) : (
                  users.map((user) => (
                    <TableRow key={user.id}>
                      <TableCell>{user.email}</TableCell>
                      <TableCell>{user.full_name}</TableCell>
                      <TableCell>
                        {isBankAdmin ? (
                          <Select
                            value={user.role}
                            onValueChange={(value: "bank_officer" | "bank_admin") =>
                              handleRoleChange(user.id, value)
                            }
                            disabled={actionId === user.id}
                          >
                            <SelectTrigger className="w-[150px]">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="bank_officer">Bank Officer</SelectItem>
                              <SelectItem value="bank_admin">Bank Admin</SelectItem>
                            </SelectContent>
                          </Select>
                        ) : (
                          <Badge variant="outline">{user.role === "bank_admin" ? "Bank Admin" : "Bank Officer"}</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <Badge variant={user.is_active ? "default" : "secondary"}>
                          {user.is_active ? "Active" : "Suspended"}
                        </Badge>
                      </TableCell>
                      <TableCell>
                        {format(new Date(user.created_at), "MMM d, yyyy")}
                      </TableCell>
                      <TableCell className="text-right">
                        {isBankAdmin && (
                          <div className="flex justify-end gap-2">
                            {user.is_active ? (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleSuspend(user.id)}
                                disabled={actionId === user.id}
                              >
                                <UserMinus className="w-4 h-4" />
                              </Button>
                            ) : (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleReactivate(user.id)}
                                disabled={actionId === user.id}
                              >
                                <RotateCcw className="w-4 h-4" />
                              </Button>
                            )}
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => handleReset2FA(user.id)}
                              disabled={actionId === user.id}
                              title="Reset 2FA"
                            >
                              <KeyRound className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                )}
              </TableBody>
            </Table>

            {totalPages > 1 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  Showing {((page - 1) * PAGE_SIZE) + 1} to {Math.min(page * PAGE_SIZE, total)} of {total} users
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

