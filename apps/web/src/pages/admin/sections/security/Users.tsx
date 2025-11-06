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

