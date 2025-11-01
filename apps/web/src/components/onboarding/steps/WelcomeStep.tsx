import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, CheckCircle, Shield, Clock } from 'lucide-react'

interface WelcomeStepProps {
  welcomeMessage?: string
}

export function WelcomeStep({ welcomeMessage }: WelcomeStepProps) {
  return (
    <div className="space-y-6">
      <div className="text-center">
        <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-primary rounded-2xl mb-6 shadow-medium">
          <FileText className="w-10 h-10 text-primary-foreground" />
        </div>
        <h2 className="text-3xl font-bold text-foreground mb-4">
          {welcomeMessage || 'Welcome to LCopilot'}
        </h2>
        <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
          AI-powered Letter of Credit validation platform. Avoid costly errors and get bank-ready in minutes.
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-4 mt-8">
        <Card className="border-gray-200/50 hover:border-primary/20 transition-all">
          <CardHeader className="text-center pb-4">
            <div className="w-12 h-12 bg-blue-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Shield className="w-6 h-6 text-blue-600" />
            </div>
            <CardTitle className="text-lg">Bank Grade Security</CardTitle>
          </CardHeader>
          <CardContent>
            <CardDescription className="text-center">
              Your documents are secured with enterprise-grade encryption
            </CardDescription>
          </CardContent>
        </Card>

        <Card className="border-gray-200/50 hover:border-primary/20 transition-all">
          <CardHeader className="text-center pb-4">
            <div className="w-12 h-12 bg-green-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <Clock className="w-6 h-6 text-green-600" />
            </div>
            <CardTitle className="text-lg">5-Minute Validation</CardTitle>
          </CardHeader>
          <CardContent>
            <CardDescription className="text-center">
              Validate your LC documents in minutes, not hours
            </CardDescription>
          </CardContent>
        </Card>

        <Card className="border-gray-200/50 hover:border-primary/20 transition-all">
          <CardHeader className="text-center pb-4">
            <div className="w-12 h-12 bg-amber-50 rounded-xl flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-6 h-6 text-amber-600" />
            </div>
            <CardTitle className="text-lg">99.9% Accuracy</CardTitle>
          </CardHeader>
          <CardContent>
            <CardDescription className="text-center">
              AI-powered validation catches discrepancies automatically
            </CardDescription>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

