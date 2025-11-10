import * as React from "react";
import { useState, useEffect } from "react";
import { useToast } from "@/hooks/use-toast";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Users, UserPlus, Mail, Crown, Edit, Eye, Shield, Trash2, X } from "lucide-react";
import { api } from "@/api/client";

interface WorkspaceMember {
  id: string;
  workspace_id: string;
  user_id: string;
  user_email?: string;
  user_name?: string;
  role: "owner" | "editor" | "viewer" | "auditor";
  invited_by?: string;
  invited_at: string;
  accepted_at?: string;
  is_active: boolean;
}

interface WorkspaceInvitation {
  id: string;
  workspace_id: string;
  email: string;
  role: "owner" | "editor" | "viewer" | "auditor";
  status: "pending" | "accepted" | "expired" | "cancelled";
  expires_at: string;
  created_at: string;
}

interface TeamRolesProps {
  workspaceId: string;
  currentUserRole?: "owner" | "editor" | "viewer" | "auditor";
}

export function TeamRoles({ workspaceId, currentUserRole = "viewer" }: TeamRolesProps) {
  const [members, setMembers] = useState<WorkspaceMember[]>([]);
  const [invitations, setInvitations] = useState<WorkspaceInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [selectedMember, setSelectedMember] = useState<WorkspaceMember | null>(null);
  const { toast } = useToast();

  const [inviteForm, setInviteForm] = useState({
    email: "",
    role: "viewer" as "owner" | "editor" | "viewer" | "auditor",
  });

  const canManageMembers = currentUserRole === "owner" || currentUserRole === "editor";
  const canEditRoles = currentUserRole === "owner";

  useEffect(() => {
    loadMembers();
    loadInvitations();
  }, [workspaceId]);

  const loadMembers = async () => {
    try {
      const response = await api.get(`/api/sme/workspaces/${workspaceId}/members`);
      setMembers(response.data.items || []);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to load team members",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const loadInvitations = async () => {
    try {
      const response = await api.get(`/api/sme/workspaces/${workspaceId}/invitations`);
      setInvitations(response.data.items || []);
    } catch (error: any) {
      // Silently fail - invitations are optional
    }
  };

  const handleInvite = async () => {
    if (!inviteForm.email) {
      toast({
        title: "Error",
        description: "Please enter an email address",
        variant: "destructive",
      });
      return;
    }

    try {
      await api.post(`/api/sme/workspaces/${workspaceId}/invite`, {
        email: inviteForm.email,
        role: inviteForm.role,
      });

      toast({
        title: "Invitation Sent",
        description: `Invitation sent to ${inviteForm.email}`,
      });

      setInviteForm({ email: "", role: "viewer" });
      setInviteDialogOpen(false);
      loadInvitations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send invitation",
        variant: "destructive",
      });
    }
  };

  const handleUpdateRole = async (memberId: string, newRole: string) => {
    try {
      await api.put(`/api/sme/workspaces/${workspaceId}/members/${memberId}`, {
        role: newRole,
      });

      toast({
        title: "Role Updated",
        description: "Member role has been updated successfully",
      });

      setEditDialogOpen(false);
      setSelectedMember(null);
      loadMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update role",
        variant: "destructive",
      });
    }
  };

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm("Are you sure you want to remove this member from the workspace?")) {
      return;
    }

    try {
      await api.delete(`/api/sme/workspaces/${workspaceId}/members/${memberId}`);

      toast({
        title: "Member Removed",
        description: "Member has been removed from the workspace",
      });

      loadMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to remove member",
        variant: "destructive",
      });
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role) {
      case "owner":
        return <Crown className="h-4 w-4 text-yellow-600" />;
      case "editor":
        return <Edit className="h-4 w-4 text-blue-600" />;
      case "viewer":
        return <Eye className="h-4 w-4 text-gray-600" />;
      case "auditor":
        return <Shield className="h-4 w-4 text-purple-600" />;
      default:
        return null;
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case "owner":
        return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200";
      case "editor":
        return "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200";
      case "viewer":
        return "bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200";
      case "auditor":
        return "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200";
      default:
        return "";
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Team Members</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">Loading...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Team Members
            </CardTitle>
            <CardDescription>
              Manage workspace access and permissions for team members and auditors
            </CardDescription>
          </div>
          {canManageMembers && (
            <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
              <DialogTrigger asChild>
                <Button size="sm">
                  <UserPlus className="mr-2 h-4 w-4" />
                  Invite Member
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Invite Team Member</DialogTitle>
                  <DialogDescription>
                    Send an invitation to join this workspace. They will receive an email with instructions.
                  </DialogDescription>
                </DialogHeader>
                <div className="space-y-4 py-4">
                  <div className="space-y-2">
                    <Label htmlFor="invite-email">Email Address</Label>
                    <Input
                      id="invite-email"
                      type="email"
                      placeholder="colleague@example.com"
                      value={inviteForm.email}
                      onChange={(e) => setInviteForm({ ...inviteForm, email: e.target.value })}
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="invite-role">Role</Label>
                    <Select
                      value={inviteForm.role}
                      onValueChange={(value: any) => setInviteForm({ ...inviteForm, role: value })}
                    >
                      <SelectTrigger id="invite-role">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="editor">
                          <div className="flex items-center gap-2">
                            <Edit className="h-4 w-4" />
                            <span>Editor - Can edit workspace and upload documents</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="viewer">
                          <div className="flex items-center gap-2">
                            <Eye className="h-4 w-4" />
                            <span>Viewer - Read-only access</span>
                          </div>
                        </SelectItem>
                        <SelectItem value="auditor">
                          <div className="flex items-center gap-2">
                            <Shield className="h-4 w-4" />
                            <span>Auditor - Read-only access for external auditors</span>
                          </div>
                        </SelectItem>
                        {canEditRoles && (
                          <SelectItem value="owner">
                            <div className="flex items-center gap-2">
                              <Crown className="h-4 w-4" />
                              <span>Owner - Full control</span>
                            </div>
                          </SelectItem>
                        )}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleInvite}>Send Invitation</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-6">
          {/* Active Members */}
          <div>
            <h3 className="text-sm font-medium mb-3">Active Members ({members.length})</h3>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Member</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Joined</TableHead>
                  {canManageMembers && <TableHead className="text-right">Actions</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {members.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">
                          {member.user_name || member.user_email || "Unknown User"}
                        </span>
                        <span className="text-xs text-muted-foreground">{member.user_email}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className={getRoleBadgeColor(member.role)}>
                        <div className="flex items-center gap-1">
                          {getRoleIcon(member.role)}
                          <span className="capitalize">{member.role}</span>
                        </div>
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="text-sm text-muted-foreground">
                        {member.accepted_at
                          ? new Date(member.accepted_at).toLocaleDateString()
                          : "Pending"}
                      </span>
                    </TableCell>
                    {canManageMembers && (
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {canEditRoles && member.role !== "owner" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => {
                                setSelectedMember(member);
                                setEditDialogOpen(true);
                              }}
                            >
                              <Edit className="h-4 w-4" />
                            </Button>
                          )}
                          {member.role !== "owner" && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => handleRemoveMember(member.id)}
                            >
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          )}
                        </div>
                      </TableCell>
                    )}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>

          {/* Pending Invitations */}
          {invitations.filter((inv) => inv.status === "pending").length > 0 && (
            <div>
              <h3 className="text-sm font-medium mb-3">Pending Invitations</h3>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Email</TableHead>
                    <TableHead>Role</TableHead>
                    <TableHead>Expires</TableHead>
                    {canManageMembers && <TableHead className="text-right">Actions</TableHead>}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invitations
                    .filter((inv) => inv.status === "pending")
                    .map((invitation) => (
                      <TableRow key={invitation.id}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <Mail className="h-4 w-4 text-muted-foreground" />
                            <span>{invitation.email}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge className={getRoleBadgeColor(invitation.role)}>
                            <span className="capitalize">{invitation.role}</span>
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <span className="text-sm text-muted-foreground">
                            {new Date(invitation.expires_at).toLocaleDateString()}
                          </span>
                        </TableCell>
                        {canManageMembers && (
                          <TableCell className="text-right">
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={async () => {
                                try {
                                  await api.delete(`/api/sme/workspaces/invitations/${invitation.id}`);
                                  toast({
                                    title: "Invitation Cancelled",
                                    description: "The invitation has been cancelled",
                                  });
                                  loadInvitations();
                                } catch (error: any) {
                                  toast({
                                    title: "Error",
                                    description: error.response?.data?.detail || "Failed to cancel invitation",
                                    variant: "destructive",
                                  });
                                }
                              }}
                            >
                              <X className="h-4 w-4" />
                            </Button>
                          </TableCell>
                        )}
                      </TableRow>
                    ))}
                </TableBody>
              </Table>
            </div>
          )}
        </div>

        {/* Edit Role Dialog */}
        <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Member Role</DialogTitle>
              <DialogDescription>
                Change the role for {selectedMember?.user_name || selectedMember?.user_email}
              </DialogDescription>
            </DialogHeader>
            {selectedMember && (
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label>Role</Label>
                  <Select
                    value={selectedMember.role}
                    onValueChange={(value: any) => {
                      handleUpdateRole(selectedMember.id, value);
                    }}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="editor">
                        <div className="flex items-center gap-2">
                          <Edit className="h-4 w-4" />
                          <span>Editor</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="viewer">
                        <div className="flex items-center gap-2">
                          <Eye className="h-4 w-4" />
                          <span>Viewer</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="auditor">
                        <div className="flex items-center gap-2">
                          <Shield className="h-4 w-4" />
                          <span>Auditor</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" onClick={() => setEditDialogOpen(false)}>
                Close
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </CardContent>
    </Card>
  );
}

