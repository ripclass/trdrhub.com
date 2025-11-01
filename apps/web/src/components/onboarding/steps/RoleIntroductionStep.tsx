import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2 } from 'lucide-react'

interface RoleIntroductionStepProps {
  role: string
  introduction: string
  keyFeatures: string[]
}

export function RoleIntroductionStep({
  role,
  introduction,
  keyFeatures,
}: RoleIntroductionStepProps) {
  const roleColors: Record<string, string> = {
    exporter: 'bg-exporter text-exporter-foreground',
    importer: 'bg-importer text-importer-foreground',
    bank_officer: 'bg-blue-500 text-white',
    bank_admin: 'bg-purple-500 text-white',
    system_admin: 'bg-gray-900 text-white',
  }

  const roleColor = roleColors[role] || 'bg-primary text-primary-foreground'

  return (
    <div className="space-y-6">
      <div className="text-center">
        <Badge className={`${roleColor} text-sm px-4 py-2 mb-4`}>
          {role.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
        </Badge>
        <h2 className="text-3xl font-bold text-foreground mb-4">
          Your Role: {role.replace('_', ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          {introduction}
        </p>
      </div>

      <Card className="border-gray-200/50">
        <CardHeader>
          <CardTitle>Key Features for Your Role</CardTitle>
          <CardDescription>
            Here's what you can do with LCopilot as a {role.replace('_', ' ')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid md:grid-cols-2 gap-4">
            {keyFeatures.map((feature, index) => (
              <div key={index} className="flex items-start gap-3">
                <CheckCircle2 className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <span className="text-foreground">{feature}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

