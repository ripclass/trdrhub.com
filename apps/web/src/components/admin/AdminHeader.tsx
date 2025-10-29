import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Bell,
  Search,
  Settings,
  LogOut,
  User,
  Shield,
  HelpCircle,
  AlertTriangle,
  CheckCircle,
  Info
} from 'lucide-react';
import { useAdminAuth } from '@/lib/admin/auth';

interface AdminUser {
  id: string;
  name: string;
  email: string;
  role: string;
  avatar?: string;
}

interface AdminHeaderProps {
  user?: AdminUser;
  onLogout?: () => void;
}

export function AdminHeader({ user, onLogout }: AdminHeaderProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const { user: currentUser, logout, permissions } = useAdminAuth();

  const adminUser = user || currentUser;

  const handleLogout = () => {
    if (onLogout) {
      onLogout();
    } else {
      logout();
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // TODO: Implement global search
      console.log('Searching for:', searchQuery);
    }
  };

  // Mock notifications for demo
  const notifications = [
    {
      id: '1',
      type: 'warning',
      title: 'High Error Rate',
      message: 'Error rate increased to 2.5% in the last hour',
      time: '5 min ago',
      unread: true
    },
    {
      id: '2',
      type: 'info',
      title: 'New Partner Onboarded',
      message: 'BankOne has completed integration setup',
      time: '1 hour ago',
      unread: true
    },
    {
      id: '3',
      type: 'success',
      title: 'Deployment Complete',
      message: 'Version 2.1.3 deployed successfully',
      time: '2 hours ago',
      unread: false
    }
  ];

  const unreadCount = notifications.filter(n => n.unread).length;

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'warning':
        return <AlertTriangle className="w-4 h-4 text-yellow-600" />;
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      default:
        return <Info className="w-4 h-4 text-blue-600" />;
    }
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'super_admin':
        return 'bg-red-100 text-red-800';
      case 'ops_admin':
        return 'bg-blue-100 text-blue-800';
      case 'security_admin':
        return 'bg-purple-100 text-purple-800';
      case 'finance_admin':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
      {/* Search */}
      <form onSubmit={handleSearch} className="flex-1 max-w-lg">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
          <Input
            type="search"
            placeholder="Search users, jobs, invoices, logs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-10 pr-4 w-full"
          />
        </div>
      </form>

      {/* Right side actions */}
      <div className="flex items-center gap-4">
        {/* Notifications */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="sm" className="relative">
              <Bell className="w-5 h-5" />
              {unreadCount > 0 && (
                <Badge
                  className="absolute -top-1 -right-1 px-1 py-0 text-xs min-w-[16px] h-4"
                  variant="destructive"
                >
                  {unreadCount}
                </Badge>
              )}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-80">
            <DropdownMenuLabel className="flex items-center justify-between">
              Notifications
              {unreadCount > 0 && (
                <Badge variant="secondary" className="text-xs">
                  {unreadCount} new
                </Badge>
              )}
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <div className="max-h-96 overflow-y-auto">
              {notifications.map((notification) => (
                <DropdownMenuItem
                  key={notification.id}
                  className={`p-3 cursor-pointer ${notification.unread ? 'bg-blue-50' : ''}`}
                >
                  <div className="flex gap-3 w-full">
                    {getNotificationIcon(notification.type)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between">
                        <p className="text-sm font-medium text-gray-900 truncate">
                          {notification.title}
                        </p>
                        {notification.unread && (
                          <div className="w-2 h-2 bg-blue-600 rounded-full ml-2 mt-1 flex-shrink-0" />
                        )}
                      </div>
                      <p className="text-xs text-gray-600 mt-1 line-clamp-2">
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {notification.time}
                      </p>
                    </div>
                  </div>
                </DropdownMenuItem>
              ))}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-8 w-8 rounded-full">
              <Avatar className="h-8 w-8">
                <AvatarImage src={adminUser?.avatar} alt={adminUser?.name} />
                <AvatarFallback>
                  {adminUser?.name?.split(' ').map(n => n[0]).join('') || 'A'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end" forceMount>
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col space-y-1">
                <p className="text-sm font-medium leading-none">
                  {adminUser?.name}
                </p>
                <p className="text-xs leading-none text-muted-foreground">
                  {adminUser?.email}
                </p>
                <Badge
                  className={`text-xs w-fit mt-1 ${getRoleBadgeColor(adminUser?.role || '')}`}
                  variant="secondary"
                >
                  <Shield className="w-3 h-3 mr-1" />
                  {adminUser?.role?.replace('_', ' ').toUpperCase()}
                </Badge>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4" />
              <span>Profile</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4" />
              <span>Settings</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <HelpCircle className="mr-2 h-4 w-4" />
              <span>Support</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} className="text-red-600">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}