/**
 * Team Management Page
 * Phase 3: Create and manage teams for collaboration
 */
import { useState, useEffect } from "react";
import { 
  Users, Plus, Settings, UserPlus, Trash2,
  Loader2, Crown, Shield, Eye, Edit, Mail
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import { useAuth } from "@/hooks/use-auth";

interface TeamMember {
  id: string;
  user_id: string;
  role: string;
  status: string;
  joined_at?: string;
}

interface Project {
  id: string;
  name: string;
  status: string;
  classification_count: number;
}

interface Team {
  id: string;
  name: string;
  description?: string;
  role: string;
  member_count: number;
  plan: string;
  created_at: string;
}

interface TeamDetail extends Team {
  owner_id: string;
  default_import_country: string;
  max_members: number;
  members: TeamMember[];
  projects: Project[];
  your_role: string;
}

const ROLE_ICONS: Record<string, typeof Crown> = {
  owner: Crown,
  admin: Shield,
  editor: Edit,
  viewer: Eye,
};

const ROLE_COLORS: Record<string, string> = {
  owner: "text-yellow-400 border-yellow-500",
  admin: "text-purple-400 border-purple-500",
  editor: "text-blue-400 border-blue-500",
  viewer: "text-slate-400 border-slate-500",
};

export default function HSCodeTeams() {
  const { token, isAuthenticated } = useAuth();
  const { toast } = useToast();
  
  const [teams, setTeams] = useState<Team[]>([]);
  const [selectedTeam, setSelectedTeam] = useState<TeamDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  
  // Create team form
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newTeamName, setNewTeamName] = useState("");
  const [newTeamDescription, setNewTeamDescription] = useState("");
  
  // Invite member form
  const [showInviteDialog, setShowInviteDialog] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("editor");

  useEffect(() => {
    if (isAuthenticated && token) {
      loadTeams();
    } else {
      setIsLoading(false);
    }
  }, [isAuthenticated, token]);

  const loadTeams = async () => {
    if (!token) return;
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/teams`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setTeams(data.teams || []);
      }
    } catch (error) {
      console.error('Failed to load teams:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const loadTeamDetail = async (teamId: string) => {
    if (!token) return;
    
    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/teams/${teamId}`,
        {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setSelectedTeam(data);
      }
    } catch (error) {
      toast({
        title: "Failed to load team",
        description: "Could not load team details",
        variant: "destructive"
      });
    }
  };

  const createTeam = async () => {
    if (!token || !newTeamName.trim()) {
      toast({
        title: "Name required",
        description: "Please enter a team name",
        variant: "destructive"
      });
      return;
    }

    setIsCreating(true);

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/teams`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            name: newTeamName,
            description: newTeamDescription,
            default_import_country: "US"
          })
        }
      );

      if (!response.ok) {
        throw new Error('Failed to create team');
      }

      const data = await response.json();
      
      toast({
        title: "Team created",
        description: `${newTeamName} has been created successfully`
      });

      setShowCreateDialog(false);
      setNewTeamName("");
      setNewTeamDescription("");
      loadTeams();
    } catch (error) {
      toast({
        title: "Failed to create team",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    } finally {
      setIsCreating(false);
    }
  };

  const inviteMember = async () => {
    if (!token || !selectedTeam || !inviteEmail.trim()) {
      toast({
        title: "Email required",
        description: "Please enter an email address",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await fetch(
        `${import.meta.env.VITE_API_URL || ''}/api/hs-code/teams/${selectedTeam.id}/invite`,
        {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            email: inviteEmail,
            role: inviteRole
          })
        }
      );

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to invite');
      }

      const data = await response.json();
      
      toast({
        title: data.status === 'added' ? "Member added" : "Invitation sent",
        description: data.message || `${inviteEmail} has been ${data.status === 'added' ? 'added to' : 'invited to'} the team`
      });

      setShowInviteDialog(false);
      setInviteEmail("");
      setInviteRole("editor");
      loadTeamDetail(selectedTeam.id);
    } catch (error) {
      toast({
        title: "Failed to invite",
        description: error instanceof Error ? error.message : 'Unknown error',
        variant: "destructive"
      });
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-slate-950 text-white">
        <div className="border-b border-slate-800 bg-slate-900/50">
          <div className="px-6 py-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-400" />
              Team Collaboration
            </h1>
            <p className="text-sm text-slate-400">
              Work together on HS code classifications
            </p>
          </div>
        </div>
        
        <div className="container mx-auto px-6 py-16 text-center">
          <Users className="h-16 w-16 text-slate-600 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-white mb-2">Sign in to create a team</h2>
          <p className="text-slate-400 mb-6">
            Collaborate with colleagues on HS code classifications
          </p>
          <Button className="bg-emerald-600 hover:bg-emerald-700">
            Sign In
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <div className="border-b border-slate-800 bg-slate-900/50">
        <div className="px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold flex items-center gap-2">
              <Users className="h-5 w-5 text-emerald-400" />
              Team Collaboration
            </h1>
            <p className="text-sm text-slate-400">
              Work together on HS code classifications
            </p>
          </div>
          <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
            <DialogTrigger asChild>
              <Button className="bg-emerald-600 hover:bg-emerald-700">
                <Plus className="h-4 w-4 mr-2" />
                Create Team
              </Button>
            </DialogTrigger>
            <DialogContent className="bg-slate-800 border-slate-700">
              <DialogHeader>
                <DialogTitle className="text-white">Create a New Team</DialogTitle>
                <DialogDescription>
                  Set up a team to collaborate on classifications
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 pt-4">
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">Team Name *</label>
                  <Input
                    placeholder="e.g., Import Team"
                    value={newTeamName}
                    onChange={(e) => setNewTeamName(e.target.value)}
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 mb-1 block">Description</label>
                  <Textarea
                    placeholder="What does this team work on?"
                    value={newTeamDescription}
                    onChange={(e) => setNewTeamDescription(e.target.value)}
                    className="bg-slate-900 border-slate-700"
                  />
                </div>
                <Button 
                  onClick={createTeam}
                  disabled={isCreating}
                  className="w-full bg-emerald-600 hover:bg-emerald-700"
                >
                  {isCreating ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    "Create Team"
                  )}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      <div className="container mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Teams List */}
          <div>
            <h2 className="text-lg font-semibold text-white mb-4">Your Teams</h2>
            
            {isLoading ? (
              <Card className="bg-slate-800 border-slate-700">
                <CardContent className="p-8 text-center">
                  <Loader2 className="h-8 w-8 animate-spin text-emerald-400 mx-auto" />
                </CardContent>
              </Card>
            ) : teams.length > 0 ? (
              <div className="space-y-3">
                {teams.map((team) => {
                  const RoleIcon = ROLE_ICONS[team.role] || Eye;
                  
                  return (
                    <Card 
                      key={team.id}
                      className={`bg-slate-800 border-slate-700 cursor-pointer transition-colors hover:border-emerald-600 ${
                        selectedTeam?.id === team.id ? 'border-emerald-500' : ''
                      }`}
                      onClick={() => loadTeamDetail(team.id)}
                    >
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div>
                            <h3 className="text-white font-medium">{team.name}</h3>
                            <p className="text-xs text-slate-500">{team.member_count} members</p>
                          </div>
                          <Badge variant="outline" className={ROLE_COLORS[team.role]}>
                            <RoleIcon className="h-3 w-3 mr-1" />
                            {team.role}
                          </Badge>
                        </div>
                        {team.description && (
                          <p className="text-sm text-slate-400 mt-2 line-clamp-2">
                            {team.description}
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  );
                })}
              </div>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-6 text-center">
                  <Users className="h-10 w-10 text-slate-600 mx-auto mb-3" />
                  <h3 className="text-white font-medium mb-1">No teams yet</h3>
                  <p className="text-sm text-slate-400 mb-4">
                    Create a team to start collaborating
                  </p>
                  <Button 
                    onClick={() => setShowCreateDialog(true)}
                    variant="outline"
                    size="sm"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create Team
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Team Detail */}
          <div className="lg:col-span-2">
            {selectedTeam ? (
              <div className="space-y-6">
                <Card className="bg-slate-800 border-slate-700">
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle className="text-white">{selectedTeam.name}</CardTitle>
                      <CardDescription>{selectedTeam.description}</CardDescription>
                    </div>
                    {(selectedTeam.your_role === 'owner' || selectedTeam.your_role === 'admin') && (
                      <div className="flex gap-2">
                        <Dialog open={showInviteDialog} onOpenChange={setShowInviteDialog}>
                          <DialogTrigger asChild>
                            <Button variant="outline" size="sm">
                              <UserPlus className="h-4 w-4 mr-2" />
                              Invite
                            </Button>
                          </DialogTrigger>
                          <DialogContent className="bg-slate-800 border-slate-700">
                            <DialogHeader>
                              <DialogTitle className="text-white">Invite Team Member</DialogTitle>
                              <DialogDescription>
                                Add someone to {selectedTeam.name}
                              </DialogDescription>
                            </DialogHeader>
                            <div className="space-y-4 pt-4">
                              <div>
                                <label className="text-sm text-slate-400 mb-1 block">Email Address</label>
                                <Input
                                  type="email"
                                  placeholder="colleague@company.com"
                                  value={inviteEmail}
                                  onChange={(e) => setInviteEmail(e.target.value)}
                                  className="bg-slate-900 border-slate-700"
                                />
                              </div>
                              <div>
                                <label className="text-sm text-slate-400 mb-1 block">Role</label>
                                <Select value={inviteRole} onValueChange={setInviteRole}>
                                  <SelectTrigger className="bg-slate-900 border-slate-700">
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value="admin">Admin - Full access</SelectItem>
                                    <SelectItem value="editor">Editor - Create & edit</SelectItem>
                                    <SelectItem value="viewer">Viewer - View only</SelectItem>
                                  </SelectContent>
                                </Select>
                              </div>
                              <Button 
                                onClick={inviteMember}
                                className="w-full bg-emerald-600 hover:bg-emerald-700"
                              >
                                <Mail className="h-4 w-4 mr-2" />
                                Send Invitation
                              </Button>
                            </div>
                          </DialogContent>
                        </Dialog>
                        <Button variant="outline" size="sm">
                          <Settings className="h-4 w-4" />
                        </Button>
                      </div>
                    )}
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-3 gap-4 mb-6">
                      <div className="bg-slate-900 p-3 rounded text-center">
                        <div className="text-xl font-bold text-white">{selectedTeam.members.length}</div>
                        <div className="text-xs text-slate-400">Members</div>
                      </div>
                      <div className="bg-slate-900 p-3 rounded text-center">
                        <div className="text-xl font-bold text-white">{selectedTeam.projects.length}</div>
                        <div className="text-xs text-slate-400">Projects</div>
                      </div>
                      <div className="bg-slate-900 p-3 rounded text-center">
                        <div className="text-xl font-bold text-white capitalize">{selectedTeam.plan}</div>
                        <div className="text-xs text-slate-400">Plan</div>
                      </div>
                    </div>

                    {/* Members */}
                    <h4 className="text-white font-medium mb-3">Team Members</h4>
                    <div className="space-y-2 mb-6">
                      {selectedTeam.members.map((member) => {
                        const RoleIcon = ROLE_ICONS[member.role] || Eye;
                        
                        return (
                          <div 
                            key={member.id}
                            className="flex items-center justify-between bg-slate-900 p-3 rounded"
                          >
                            <div className="flex items-center gap-3">
                              <div className="h-8 w-8 rounded-full bg-emerald-500/20 flex items-center justify-center">
                                <span className="text-sm font-medium text-emerald-400">
                                  {member.user_id.charAt(0).toUpperCase()}
                                </span>
                              </div>
                              <div>
                                <div className="text-white text-sm">User {member.user_id.substring(0, 8)}</div>
                                <div className="text-xs text-slate-500 capitalize">{member.status}</div>
                              </div>
                            </div>
                            <Badge variant="outline" className={ROLE_COLORS[member.role]}>
                              <RoleIcon className="h-3 w-3 mr-1" />
                              {member.role}
                            </Badge>
                          </div>
                        );
                      })}
                    </div>

                    {/* Projects */}
                    {selectedTeam.projects.length > 0 && (
                      <>
                        <h4 className="text-white font-medium mb-3">Projects</h4>
                        <div className="grid grid-cols-2 gap-3">
                          {selectedTeam.projects.map((project) => (
                            <div 
                              key={project.id}
                              className="bg-slate-900 p-3 rounded"
                            >
                              <div className="text-white font-medium">{project.name}</div>
                              <div className="flex items-center gap-2 mt-1">
                                <Badge variant="outline" className="text-xs capitalize">
                                  {project.status}
                                </Badge>
                                <span className="text-xs text-slate-500">
                                  {project.classification_count} classifications
                                </span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              </div>
            ) : (
              <Card className="bg-slate-800/50 border-slate-700">
                <CardContent className="p-12 text-center">
                  <Users className="h-12 w-12 text-slate-600 mx-auto mb-4" />
                  <h3 className="text-white font-medium mb-2">Select a Team</h3>
                  <p className="text-slate-400 text-sm">
                    Choose a team from the list to view details and members
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

