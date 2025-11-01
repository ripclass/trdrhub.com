import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { 
  LayoutDashboard, 
  FileText, 
  BarChart3, 
  Settings,
  Upload,
  CheckCircle,
  Download
} from 'lucide-react'

interface PlatformOverviewStepProps {
  role: string
}

export function PlatformOverviewStep({ role }: PlatformOverviewStepProps) {
  const isExporter = role === 'exporter'
  const isImporter = role === 'importer'
  const isBank = role === 'bank_officer' || role === 'bank_admin'
  const isAdmin = role === 'system_admin'

  const navigationItems = [
    {
      icon: LayoutDashboard,
      title: 'Dashboard',
      description: isBank || isAdmin
        ? 'System-wide analytics and monitoring'
        : 'Your validation history and statistics',
      available: true,
    },
    {
      icon: isBank || isAdmin ? BarChart3 : Upload,
      title: isBank || isAdmin ? 'Analytics' : 'Upload Documents',
      description: isBank || isAdmin
        ? 'Comprehensive analytics across all tenants'
        : 'Upload and validate your LC documents',
      available: !isBank && !isAdmin,
    },
    {
      icon: isBank || isAdmin ? FileText : CheckCircle,
      title: isBank || isAdmin ? 'Compliance Reports' : 'Review Results',
      description: isBank || isAdmin
        ? 'Generate compliance and audit reports'
        : 'Review discrepancies and validation results',
      available: true,
    },
    {
      icon: isBank || isAdmin ? BarChart3 : Download,
      title: isBank || isAdmin ? 'Audit Trails' : 'Generate Reports',
      description: isBank || isAdmin
        ? 'Access complete audit trails and logs'
        : 'Download validation reports and evidence packs',
      available: true,
    },
    {
      icon: Settings,
      title: 'Settings',
      description: 'Configure your account and preferences',
      available: true,
    },
  ]

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-foreground mb-4">
          Platform Overview
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          Navigate the platform and understand key areas
        </p>
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4 mt-8">
        {navigationItems
          .filter((item) => item.available)
          .map((item, index) => {
            const Icon = item.icon
            return (
              <Card
                key={index}
                className="border-gray-200/50 hover:border-primary/20 transition-all cursor-pointer"
              >
                <CardHeader className="pb-4">
                  <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center mb-4">
                    <Icon className="w-6 h-6 text-primary" />
                  </div>
                  <CardTitle className="text-lg">{item.title}</CardTitle>
                </CardHeader>
                <CardContent>
                  <CardDescription>{item.description}</CardDescription>
                </CardContent>
              </Card>
            )
          })}
      </div>
    </div>
  )
}

