import * as React from "react";
import { useSearchParams } from "react-router-dom";

import { AdminEmptyState, AdminFilters, AdminToolbar, DataTable } from "@/components/admin/ui";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
import {
  Pagination,
  PaginationContent,
  PaginationItem,
  PaginationNext,
  PaginationPrevious,
} from "@/components/ui/pagination";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { useToast } from "@/components/ui/use-toast";
import { Shield, UserMinus, UserPlus } from "lucide-react";

import { getAdminService } from "@/lib/admin/services";
import type { AdminRole, AdminUser, RoleDefinition } from "@/lib/admin/types";
import { useAdminAudit } from "@/lib/admin/useAdminAudit";

const service = getAdminService();
const PAGE_SIZE = 10;

export default function Users() {
  const { toast } = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = React.useState(() => Math.max(1, Number(searchParams.get("usersPage") ?? "1")));
  const [searchTerm, setSearchTerm] = React.useState(searchParams.get("usersSearch") ?? "");
  const [roleFilter, setRoleFilter] = React.useState<AdminRole | "all">((searchParams.get("usersRole") as AdminRole) ?? "all");

  const [users, setUsers] = React.useState<AdminUser[]>([]);
  const [total, setTotal] = React.useState(0);
  const [roles, setRoles] = React.useState<RoleDefinition[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [actionId, setActionId] = React.useState<string | null>(null);
  const audit = useAdminAudit("security-users");

  const [inviteOpen, setInviteOpen] = React.useState(false);
  const [inviteEmail, setInviteEmail] = React.useState("");
  const [inviteRole, setInviteRole] = React.useState<AdminRole>("viewer");

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  const updateQuery = React.useCallback(
    (updates: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams);
      Object.entries(updates).forEach(([key, value]) => {
        if (!value) next.delete(key);
        else next.set(key, value);
      });
      setSearchParams(next, { replace: true });
    },
    [searchParams, setSearchParams],
  );

  const loadUsers = React.useCallback(() => {
    setLoading(true);
    service
      .listUsers({
        page,
        pageSize: PAGE_SIZE,
        search: searchTerm || undefined,
        role: roleFilter,
      })
      .then((result) => {
        setUsers(result.items);
        setTotal(result.total);
      })
      .finally(() => setLoading(false));
  }, [page, searchTerm, roleFilter]);

  React.useEffect(() => {
    service.listRoles().then(setRoles);
  }, []);

  React.useEffect(() => {
    updateQuery({
      usersPage: page === 1 ? null : String(page),
      usersSearch: searchTerm || null,
      usersRole: roleFilter !== "all" ? roleFilter : null,
    });
    loadUsers();
  }, [page, searchTerm, roleFilter, loadUsers, updateQuery]);

  const handleInvite = async () => {
    const email = inviteEmail.trim();
    if (!email) {
      toast({ title: "Email required", variant: "destructive" });
      return;
    }
    setActionId("invite");
    const result = await service.inviteUser({ email, role: inviteRole });
    setActionId(null);
    if (result.success) {
      toast({ title: "Invitation sent", description: email });
      setInviteEmail("");
      setInviteOpen(false);
      loadUsers();
      await audit("invite_user", { metadata: { email, role: inviteRole } });
    } else {
      toast({ title: "Invite failed", description: result.message, variant: "destructive" });
    }
  };

  const handleDisable = async (userId: string) => {
    setActionId(userId);
    const result = await service.disableUser(userId);
    setActionId(null);
    toast({
      title: result.success ? "User disabled" : "Disable failed",
      description: result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("disable_user", { entityId: userId });
      loadUsers();
    }
  };

  const handleRoleChange = async (userId: string, role: AdminRole) => {
    setActionId(userId);
    const result = await service.updateUserRole(userId, role);
    setActionId(null);
    toast({
      title: result.success ? "Role updated" : "Update failed",
      description: result.success ? result.data?.email : result.message,
      variant: result.success ? "default" : "destructive",
    });
    if (result.success) {
      await audit("update_user_role", { entityId: userId, metadata: { role } });
      loadUsers();
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <AdminToolbar
        title="User administration"
        description="Invite administrators, manage access and enforce least privilege."
        actions={
          <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <UserPlus className="h-4 w-4" /> Invite user
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Invite new administrator</DialogTitle>
                <DialogDescription>Send an email invite with role assignment.</DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground" htmlFor="invite-email">
                    Email
                  </label>
                  <Input
                    id="invite-email"
                    placeholder="admin@company.com"
                    value={inviteEmail}
                    onChange={(event) => setInviteEmail(event.target.value)}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-xs font-medium text-muted-foreground">Role</label>
                  <Select value={inviteRole} onValueChange={(value) => setInviteRole(value as AdminRole)}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select role" />
                    </SelectTrigger>
                    <SelectContent>
                      {roles.map((role) => (
                        <SelectItem key={role.id} value={role.id}>
                          <div className="flex flex-col text-left">
                            <span className="text-sm font-medium">{role.name}</span>
                            <span className="text-xs text-muted-foreground">{role.description}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <DialogFooter>
                <Button onClick={handleInvite} disabled={actionId === "invite"}>
                  Send invite
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        }
      >
        <AdminFilters
          searchPlaceholder="Search by name or email"
          searchValue={searchTerm}
          onSearchChange={(value) => {
            setSearchTerm(value);
            setPage(1);
          }}
          filterGroups={[
            {
              label: "Role",
              value: roleFilter,
              options: [{ label: "All roles", value: "all" as const }, ...roles.map((role) => ({ label: role.name, value: role.id }))],
              onChange: (value) => {
                setRoleFilter((value as AdminRole) || "all");
                setPage(1);
              },
              allowClear: true,
            },
          ]}
        />
      </AdminToolbar>

      <DataTable
        columns={[
          {
            key: "name",
            header: "User",
            render: (user) => (
              <div className="flex items-center gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                  {(user.name ?? user.email).charAt(0).toUpperCase()}
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">{user.name ?? "—"}</p>
                  <p className="text-xs text-muted-foreground">{user.email}</p>
                </div>
              </div>
            ),
          },
          {
            key: "role",
            header: "Role",
            render: (user) => (
              <Select
                value={user.role}
                onValueChange={(value) => handleRoleChange(user.id, value as AdminRole)}
                disabled={actionId === user.id}
              >
                <SelectTrigger className="h-9 w-[170px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {roles.map((role) => (
                    <SelectItem key={role.id} value={role.id} disabled={role.editable === false}>
                      {role.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            ),
          },
          {
            key: "status",
            header: "Status",
            render: (user) => (
              <Badge variant={user.status === "active" ? "default" : user.status === "invited" ? "secondary" : "outline"}>
                {user.status}
              </Badge>
            ),
          },
          {
            key: "lastActiveAt",
            header: "Last active",
            render: (user) => (
              <span className="text-sm text-muted-foreground">{user.lastActiveAt ? new Date(user.lastActiveAt).toLocaleString() : "—"}</span>
            ),
          },
          {
            key: "tenants",
            header: "Tenants",
            render: (user) => (
              <div className="flex flex-wrap gap-1">
                {user.tenants.map((tenant) => (
                  <Badge key={tenant} variant="outline" className="text-[10px]">
                    {tenant}
                  </Badge>
                ))}
              </div>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            align: "right",
            render: (user) => (
              <div className="flex items-center justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-1 text-rose-600"
                  disabled={user.status !== "active" || actionId === user.id}
                  onClick={() => handleDisable(user.id)}
                >
                  <UserMinus className="h-4 w-4" /> Disable
                </Button>
              </div>
            ),
          },
        ]}
        data={users}
        loading={loading}
        emptyState={<AdminEmptyState title="No users" description="Try adjusting the role filter." />}
        footer={
          total > PAGE_SIZE && (
            <Pagination>
              <PaginationContent>
                <PaginationItem>
                  <PaginationPrevious
                    href="#"
                    className={page === 1 ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page > 1) setPage(page - 1);
                    }}
                  />
                </PaginationItem>
                <PaginationItem>
                  <span className="text-sm text-muted-foreground">Page {page} of {totalPages}</span>
                </PaginationItem>
                <PaginationItem>
                  <PaginationNext
                    href="#"
                    className={page >= totalPages ? "pointer-events-none opacity-50" : undefined}
                    onClick={(event) => {
                      event.preventDefault();
                      if (page < totalPages) setPage(page + 1);
                    }}
                  />
                </PaginationItem>
              </PaginationContent>
            </Pagination>
          )
        }
      />

      {loading && users.length === 0 && (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-12 w-full" />
          ))}
        </div>
      )}

      <div className="rounded-lg border border-border/60 bg-muted/30 p-4">
        <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-muted-foreground">
          <Shield className="h-4 w-4" /> Policy tip
        </h3>
        <p className="text-xs text-muted-foreground">
          Enforce multi-factor authentication and review inactive invites regularly. Promote temporary access using
          the invite flow rather than sharing credentials.
        </p>
      </div>
    </div>
  );
}
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Users as UsersIcon, Search, Plus, Edit, Trash2 } from 'lucide-react';

const mockUsers = [
  { id: 'user-001', name: 'John Doe', email: 'admin@lcopilot.com', role: 'super_admin', status: 'active', lastLogin: '2 min ago' },
  { id: 'user-002', name: 'Jane Smith', email: 'ops@lcopilot.com', role: 'ops_admin', status: 'active', lastLogin: '1 hour ago' },
  { id: 'user-003', name: 'Bob Wilson', email: 'security@lcopilot.com', role: 'security_admin', status: 'active', lastLogin: '3 hours ago' },
  { id: 'user-004', name: 'Alice Brown', email: 'finance@lcopilot.com', role: 'finance_admin', status: 'inactive', lastLogin: '2 days ago' },
];

export function SecurityUsers() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Users & Tenants</h2>
        <p className="text-muted-foreground">
          Manage system users, roles, and tenant organizations
        </p>
      </div>

      <Card className="shadow-soft border-0">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <UsersIcon className="w-5 h-5" />
            User Management
          </CardTitle>
          <CardDescription>View and manage all system users</CardDescription>
          <div className="flex gap-2 mt-4">
            <Input placeholder="Search users..." className="max-w-sm" />
            <Button>
              <Plus className="w-4 h-4 mr-2" />
              Add User
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {mockUsers.map((user) => (
              <div key={user.id} className="flex items-center justify-between p-3 border rounded-lg">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                    <span className="font-semibold text-primary">{user.name.charAt(0)}</span>
                  </div>
                  <div>
                    <p className="font-medium text-foreground">{user.name}</p>
                    <p className="text-sm text-muted-foreground">{user.email}</p>
                  </div>
                  <Badge variant="outline">{user.role.replace('_', ' ')}</Badge>
                  <Badge variant={user.status === 'active' ? 'default' : 'secondary'}>
                    {user.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted-foreground">{user.lastLogin}</span>
                  <div className="flex gap-2">
                    <Button variant="outline" size="sm">
                      <Edit className="w-4 h-4" />
                    </Button>
                    <Button variant="outline" size="sm" className="text-destructive">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
}

