import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Users, Settings, BarChart3, Shield } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

interface AdminOnboardingStepsProps {
  stepId: string
  onNext?: () => void
}

export function AdminOnboardingSteps({ stepId, onNext }: AdminOnboardingStepsProps) {
  if (stepId === 'admin-users') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-900/10 rounded-xl mb-4">
            <Users className="w-8 h-8 text-gray-900" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">User Management</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Manage all users and roles system-wide
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>User Management Features</CardTitle>
            <CardDescription>Complete control over system users</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <Users className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">System-Wide User Management</h4>
                  <p className="text-sm text-muted-foreground">
                    Create, edit, and manage all users across all tenants
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Role Assignment</h4>
                  <p className="text-sm text-muted-foreground">
                    Assign and modify roles for any user
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">User Analytics</h4>
                  <p className="text-sm text-muted-foreground">
                    View usage statistics and activity for all users
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button asChild className="bg-gradient-primary hover:opacity-90">
            <Link to="/admin">Go to Admin Dashboard</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (stepId === 'admin-config') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-xl mb-4">
            <Settings className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">System Configuration</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Configure system settings and preferences
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Configuration Options</CardTitle>
            <CardDescription>What you can configure</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <Settings className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">System Settings</h4>
                  <p className="text-sm text-muted-foreground">
                    Configure global system settings and preferences
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Security Settings</h4>
                  <p className="text-sm text-muted-foreground">
                    Manage security policies and access controls
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Feature Flags</h4>
                  <p className="text-sm text-muted-foreground">
                    Enable or disable features system-wide
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (stepId === 'admin-monitoring') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-green-50 rounded-xl mb-4">
            <BarChart3 className="w-8 h-8 text-green-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">System Monitoring</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Monitor system health and performance
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Monitoring Features</CardTitle>
            <CardDescription>Real-time system insights</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Performance Metrics</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitor system performance and resource usage
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Health Checks</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitor system health and service availability
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Users className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Usage Analytics</h4>
                  <p className="text-sm text-muted-foreground">
                    Track system-wide usage and activity patterns
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return null
}

