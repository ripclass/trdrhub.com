import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileCheck, AlertTriangle, Shield, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

interface ImporterOnboardingStepsProps {
  stepId: string
  onNext?: () => void
}

export function ImporterOnboardingSteps({ stepId, onNext }: ImporterOnboardingStepsProps) {
  if (stepId === 'importer-review') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-importer/10 rounded-xl mb-4">
            <FileCheck className="w-8 h-8 text-importer" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Review Supplier Documents</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Learn how to review supplier documents for compliance with LC requirements
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Document Review Process</CardTitle>
            <CardDescription>Simple steps to review supplier documents</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-importer/10 rounded-full flex items-center justify-center text-importer font-semibold">
                1
              </div>
              <div>
                <h4 className="font-semibold mb-1">Receive Documents</h4>
                <p className="text-sm text-muted-foreground">
                  Suppliers upload documents for your review
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-importer/10 rounded-full flex items-center justify-center text-importer font-semibold">
                2
              </div>
              <div>
                <h4 className="font-semibold mb-1">Automated Validation</h4>
                <p className="text-sm text-muted-foreground">
                  AI validates documents against LC requirements automatically
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-importer/10 rounded-full flex items-center justify-center text-importer font-semibold">
                3
              </div>
              <div>
                <h4 className="font-semibold mb-1">Review & Approve</h4>
                <p className="text-sm text-muted-foreground">
                  Review validation results and approve or request corrections
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button asChild className="bg-gradient-importer hover:opacity-90">
            <Link to="/lcopilot/importer-dashboard">View Dashboard</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (stepId === 'importer-risk') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-amber-50 rounded-xl mb-4">
            <AlertTriangle className="w-8 h-8 text-amber-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Risk Assessment</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Understand risk assessment and compliance checking for supplier documents
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Risk Factors</CardTitle>
            <CardDescription>What we check during risk assessment</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 items-start">
              <Shield className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-semibold mb-1">Document Authenticity</h4>
                <p className="text-sm text-muted-foreground">
                  Verify documents are genuine and not altered
                </p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-semibold mb-1">LC Compliance</h4>
                <p className="text-sm text-muted-foreground">
                  Check documents meet all LC requirements
                </p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <AlertTriangle className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="font-semibold mb-1">Risk Indicators</h4>
                <p className="text-sm text-muted-foreground">
                  Identify potential fraud or compliance risks
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return null
}

