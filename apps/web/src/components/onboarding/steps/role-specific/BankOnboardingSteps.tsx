import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { BarChart3, FileText, Shield, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

interface BankOnboardingStepsProps {
  stepId: string
  onNext?: () => void
}

export function BankOnboardingSteps({ stepId, onNext }: BankOnboardingStepsProps) {
  if (stepId === 'bank-monitoring' || stepId === 'bank-admin-monitoring') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-50 rounded-xl mb-4">
            <Shield className="w-8 h-8 text-blue-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Compliance Monitoring</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Monitor compliance across all tenants and users in real-time
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Monitoring Features</CardTitle>
            <CardDescription>What you can monitor as a bank officer</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex gap-3 items-start">
                <Users className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Multi-Tenant View</h4>
                  <p className="text-sm text-muted-foreground">
                    Monitor all exporters and importers across the platform
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Validation Activity</h4>
                  <p className="text-sm text-muted-foreground">
                    Track all LC validations and document processing
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Compliance Status</h4>
                  <p className="text-sm text-muted-foreground">
                    Real-time compliance status across all tenants
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Performance Metrics</h4>
                  <p className="text-sm text-muted-foreground">
                    System-wide performance and usage metrics
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button asChild className="bg-gradient-primary hover:opacity-90">
            <Link to="/lcopilot/analytics/bank">View Analytics</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (stepId === 'bank-analytics' || stepId === 'bank-admin-analytics') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-50 rounded-xl mb-4">
            <BarChart3 className="w-8 h-8 text-purple-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Analytics Dashboard</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Access comprehensive analytics and reporting across all tenants
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Analytics Features</CardTitle>
            <CardDescription>Powerful insights at your fingertips</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">System-Wide Analytics</h4>
                  <p className="text-sm text-muted-foreground">
                    View analytics across all tenants and users
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Compliance Reports</h4>
                  <p className="text-sm text-muted-foreground">
                    Generate compliance and audit reports
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Users className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Tenant Performance</h4>
                  <p className="text-sm text-muted-foreground">
                    Track performance metrics per tenant
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (stepId === 'bank-audit') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-gray-50 rounded-xl mb-4">
            <FileText className="w-8 h-8 text-gray-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Audit Trail Access</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Review audit trails and compliance data across all tenants
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Audit Features</CardTitle>
            <CardDescription>Complete audit trail access</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Immutable Audit Logs</h4>
                  <p className="text-sm text-muted-foreground">
                    Access tamper-proof audit logs for all activities
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Compliance Verification</h4>
                  <p className="text-sm text-muted-foreground">
                    Verify compliance with regulatory requirements
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <BarChart3 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Export & Reporting</h4>
                  <p className="text-sm text-muted-foreground">
                    Export audit trails for compliance reporting
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (stepId === 'bank-admin-management') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-50 rounded-xl mb-4">
            <Users className="w-8 h-8 text-purple-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">User Management</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Manage users and roles across all tenants
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Management Features</CardTitle>
            <CardDescription>What you can manage as a bank admin</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex gap-4 items-start">
                <Users className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">User Management</h4>
                  <p className="text-sm text-muted-foreground">
                    View and manage all users across tenants
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Role Management</h4>
                  <p className="text-sm text-muted-foreground">
                    Assign and modify user roles
                  </p>
                </div>
              </div>
              <div className="flex gap-4 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Tenant Administration</h4>
                  <p className="text-sm text-muted-foreground">
                    Manage tenant settings and configurations
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

