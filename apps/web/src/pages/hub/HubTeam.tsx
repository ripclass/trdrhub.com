/**
 * Hub Team - Team Member Management
 * 
 * Manage team members, roles, and invitations.
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  Mail,
  MoreVertical,
  Shield,
  UserPlus,
  Users,
  Crown,
  Trash2,
  Edit2,
  Clock,
  XCircle,
  Send,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useToast } from "@/hooks/use-toast";

const API_BASE = import.meta.env.VITE_API_URL || "";

interface TeamMember {
  id: string;
  email: string;
  name: string;
  role: "owner" | "admin" | "member" | "viewer";
  status: "active" | "invited" | "disabled";
  last_active?: string;
  invited_at?: string;
}

interface Invitation {
  id: string;
  email: string;
  role: string;
  status: "pending" | "expired";
  created_at: string;
  expires_at: string;
}

const ROLE_DESCRIPTIONS: Record<string, string> = {
  owner: "Full access including billing and team management",
  admin: "Can manage team members and all tools",
  member: "Can use all tools and view reports",
  viewer: "Read-only access to reports and analytics",
};

const ROLE_COLORS: Record<string, string> = {
  owner: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  admin: "bg-purple-500/10 text-purple-400 border-purple-500/20",
  member: "bg-blue-500/10 text-blue-400 border-blue-500/20",
  viewer: "bg-slate-500/10 text-slate-400 border-slate-500/20",
};

export default function HubTeam() {
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [maxUsers, setMaxUsers] = useState(1);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState<string>("member");
  const [inviting, setInviting] = useState(false);

  useEffect(() => {
    fetchTeamData();
  }, []);

  const fetchTeamData = async () => {
    setLoading(true);
    try {
      // For demo, show mock data
      // In production, this would fetch from /api/team
      setMembers([
        {
          id: "1",
          email: "owner@company.com",
          name: "You",
          role: "owner",
          status: "active",
          last_active: new Date().toISOString(),
        },
      ]);
      setInvitations([]);
      setMaxUsers(5); // From subscription plan

    } catch (error) {
      console.error("Failed to fetch team data:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleInvite = async () => {
    if (!inviteEmail) return;

    setInviting(true);
    try {
      // In production, POST to /api/team/invite
      toast({
        title: "Invitation Sent",
        description: `Invitation sent to ${inviteEmail}`,
      });

      setInvitations([
        ...invitations,
        {
          id: Date.now().toString(),
          email: inviteEmail,
          role: inviteRole,
          status: "pending",
          created_at: new Date().toISOString(),
          expires_at: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString(),
        },
      ]);

      setInviteEmail("");
      setInviteDialogOpen(false);
    } catch (error) {
      toast({
        title: "Error",
        description: "Failed to send invitation",
        variant: "destructive",
      });
    } finally {
      setInviting(false);
    }
  };

  const handleResendInvite = async (invitation: Invitation) => {
    toast({
      title: "Invitation Resent",
      description: `New invitation sent to ${invitation.email}`,
    });
  };

  const handleCancelInvite = async (invitation: Invitation) => {
    setInvitations(invitations.filter((i) => i.id !== invitation.id));
    toast({
      title: "Invitation Cancelled",
      description: `Invitation to ${invitation.email} has been cancelled`,
    });
  };

  const handleRemoveMember = async (member: TeamMember) => {
    if (member.role === "owner") {
      toast({
        title: "Cannot remove owner",
        description: "Transfer ownership first before leaving the team",
        variant: "destructive",
      });
      return;
    }

    setMembers(members.filter((m) => m.id !== member.id));
    toast({
      title: "Member Removed",
      description: `${member.name || member.email} has been removed from the team`,
    });
  };

  const handleChangeRole = async (member: TeamMember, newRole: string) => {
    setMembers(
      members.map((m) =>
        m.id === member.id ? { ...m, role: newRole as TeamMember["role"] } : m
      )
    );
    toast({
      title: "Role Updated",
      description: `${member.name || member.email} is now a ${newRole}`,
    });
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const formatTimeAgo = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return formatDate(dateStr);
  };

  const canInviteMore = members.length + invitations.length < maxUsers;

  return (
    <div className="p-6 lg:p-8">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-white">Team Management</h1>
          <p className="text-slate-400">
            {members.length} of {maxUsers} seats used
          </p>
        </div>
        <Button
          onClick={() => setInviteDialogOpen(true)}
          disabled={!canInviteMore}
          className="bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600 text-white"
        >
          <UserPlus className="w-4 h-4 mr-2" />
          Invite Member
        </Button>
      </div>
        {/* Team Members */}
        <Card className="mb-8 bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Users className="w-5 h-5 text-blue-400" />
              Team Members
            </CardTitle>
            <CardDescription className="text-slate-400">
              People who have access to your TRDR Hub workspace
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {members.map((member) => (
                <div
                  key={member.id}
                  className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-white/5"
                >
                  <div className="flex items-center gap-4">
                    <Avatar className="h-10 w-10">
                      <AvatarFallback
                        className={`${
                          member.role === "owner"
                            ? "bg-gradient-to-br from-amber-500 to-orange-500"
                            : "bg-gradient-to-br from-blue-500 to-emerald-500"
                        } text-white`}
                      >
                        {member.name?.charAt(0).toUpperCase() ||
                          member.email.charAt(0).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-white">
                          {member.name || member.email}
                        </span>
                        {member.role === "owner" && (
                          <Crown className="w-4 h-4 text-amber-400" />
                        )}
                      </div>
                      <p className="text-sm text-slate-400">{member.email}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4">
                    <div className="text-right hidden sm:block">
                      <Badge
                        variant="outline"
                        className={ROLE_COLORS[member.role]}
                      >
                        {member.role.charAt(0).toUpperCase() + member.role.slice(1)}
                      </Badge>
                      <p className="text-xs text-slate-500 mt-1">
                        {member.last_active
                          ? `Active ${formatTimeAgo(member.last_active)}`
                          : "Never logged in"}
                      </p>
                    </div>

                    {member.role !== "owner" && (
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4 text-slate-400" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent
                          align="end"
                          className="bg-slate-900 border-white/10"
                        >
                          <DropdownMenuItem
                            className="text-slate-300"
                            onClick={() => handleChangeRole(member, "admin")}
                          >
                            <Shield className="w-4 h-4 mr-2" />
                            Make Admin
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-slate-300"
                            onClick={() => handleChangeRole(member, "member")}
                          >
                            <Users className="w-4 h-4 mr-2" />
                            Make Member
                          </DropdownMenuItem>
                          <DropdownMenuItem
                            className="text-slate-300"
                            onClick={() => handleChangeRole(member, "viewer")}
                          >
                            <Edit2 className="w-4 h-4 mr-2" />
                            Make Viewer
                          </DropdownMenuItem>
                          <DropdownMenuSeparator className="bg-white/10" />
                          <DropdownMenuItem
                            className="text-red-400"
                            onClick={() => handleRemoveMember(member)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Pending Invitations */}
        {invitations.length > 0 && (
          <Card className="mb-8 bg-slate-900/50 border-white/5">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Mail className="w-5 h-5 text-amber-400" />
                Pending Invitations
              </CardTitle>
              <CardDescription className="text-slate-400">
                Invitations awaiting acceptance
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {invitations.map((invitation) => (
                  <div
                    key={invitation.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-amber-500/20"
                  >
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-full bg-amber-500/10 flex items-center justify-center">
                        <Clock className="w-5 h-5 text-amber-400" />
                      </div>
                      <div>
                        <p className="font-medium text-white">{invitation.email}</p>
                        <p className="text-sm text-slate-400">
                          Invited as{" "}
                          <span className="text-slate-300">{invitation.role}</span> •
                          Expires {formatDate(invitation.expires_at)}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-slate-400 hover:text-white"
                        onClick={() => handleResendInvite(invitation)}
                      >
                        <Send className="w-4 h-4 mr-1" />
                        Resend
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-red-400 hover:text-red-300"
                        onClick={() => handleCancelInvite(invitation)}
                      >
                        <XCircle className="w-4 h-4 mr-1" />
                        Cancel
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Role Descriptions */}
        <Card className="bg-slate-900/50 border-white/5">
          <CardHeader>
            <CardTitle className="text-white">Role Permissions</CardTitle>
            <CardDescription className="text-slate-400">
              Understanding what each role can do
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(ROLE_DESCRIPTIONS).map(([role, description]) => (
                <div
                  key={role}
                  className="p-4 rounded-lg bg-slate-800/50 border border-white/5"
                >
                  <Badge variant="outline" className={ROLE_COLORS[role]}>
                    {role === "owner" && <Crown className="w-3 h-3 mr-1" />}
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </Badge>
                  <p className="text-sm text-slate-400 mt-2">{description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Upgrade CTA if at limit */}
        {!canInviteMore && (
          <Card className="mt-8 bg-gradient-to-r from-blue-500/10 to-emerald-500/10 border-white/10">
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white mb-1">
                    Need more team members?
                  </h3>
                  <p className="text-slate-400 text-sm">
                    Upgrade your plan to add more users to your workspace.
                  </p>
                </div>
                <Button
                  className="bg-gradient-to-r from-blue-500 to-emerald-500 hover:from-blue-600 hover:to-emerald-600 text-white"
                  onClick={() => navigate("/hub/billing")}
                >
                  Upgrade Plan
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

      {/* Invite Dialog */}
      <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
        <DialogContent className="bg-slate-900 border-white/10">
          <DialogHeader>
            <DialogTitle className="text-white">Invite Team Member</DialogTitle>
            <DialogDescription className="text-slate-400">
              Send an invitation to join your TRDR Hub workspace.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-slate-300">
                Email Address
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="colleague@company.com"
                value={inviteEmail}
                onChange={(e) => setInviteEmail(e.target.value)}
                className="bg-slate-800 border-white/10 text-white"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="role" className="text-slate-300">
                Role
              </Label>
              <Select value={inviteRole} onValueChange={setInviteRole}>
                <SelectTrigger className="bg-slate-800 border-white/10 text-white">
                  <SelectValue placeholder="Select a role" />
                </SelectTrigger>
                <SelectContent className="bg-slate-900 border-white/10">
                  <SelectItem value="admin">Admin</SelectItem>
                  <SelectItem value="member">Member</SelectItem>
                  <SelectItem value="viewer">Viewer</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-xs text-slate-500">{ROLE_DESCRIPTIONS[inviteRole]}</p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setInviteDialogOpen(false)}
              className="border-white/10 text-slate-300"
            >
              Cancel
            </Button>
            <Button
              onClick={handleInvite}
              disabled={!inviteEmail || inviting}
              className="bg-gradient-to-r from-blue-500 to-emerald-500 text-white"
            >
              {inviting ? "Sending..." : "Send Invitation"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

