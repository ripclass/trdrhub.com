import React from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Upload, FileCheck, AlertTriangle, Download, FileText } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Link } from 'react-router-dom'

interface ExporterOnboardingStepsProps {
  stepId: string
  onNext?: () => void
}

export function ExporterOnboardingSteps({ stepId, onNext }: ExporterOnboardingStepsProps) {
  if (stepId === 'exporter-upload') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-exporter/10 rounded-xl mb-4">
            <Upload className="w-8 h-8 text-exporter" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Upload LC Documents</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Upload your Letter of Credit and supporting documents for AI-powered validation
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>How to Upload</CardTitle>
            <CardDescription>Simple steps to get started</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-exporter/10 rounded-full flex items-center justify-center text-exporter font-semibold">
                1
              </div>
              <div>
                <h4 className="font-semibold mb-1">Select Documents</h4>
                <p className="text-sm text-muted-foreground">
                  Choose your LC document and supporting files (Invoice, BL, etc.)
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-exporter/10 rounded-full flex items-center justify-center text-exporter font-semibold">
                2
              </div>
              <div>
                <h4 className="font-semibold mb-1">Upload & Process</h4>
                <p className="text-sm text-muted-foreground">
                  Our AI extracts data and validates against ICC rules automatically
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="flex-shrink-0 w-8 h-8 bg-exporter/10 rounded-full flex items-center justify-center text-exporter font-semibold">
                3
              </div>
              <div>
                <h4 className="font-semibold mb-1">Review Results</h4>
                <p className="text-sm text-muted-foreground">
                  Check for discrepancies and validation results in minutes
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="text-center">
          <Button asChild className="bg-gradient-exporter hover:opacity-90">
            <Link to="/lcopilot/upload">Try Upload Now</Link>
          </Button>
        </div>
      </div>
    )
  }

  if (stepId === 'exporter-validation') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-amber-50 rounded-xl mb-4">
            <AlertTriangle className="w-8 h-8 text-amber-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Review Discrepancies</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Understand how to review and fix discrepancies found during validation
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Discrepancy Types</CardTitle>
            <CardDescription>Understanding validation results</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-3 h-3 bg-red-500 rounded-full mt-2"></div>
              <div>
                <h4 className="font-semibold mb-1">Critical Discrepancies</h4>
                <p className="text-sm text-muted-foreground">
                  Must be fixed before submission - these will cause rejection
                </p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-3 h-3 bg-yellow-500 rounded-full mt-2"></div>
              <div>
                <h4 className="font-semibold mb-1">Major Discrepancies</h4>
                <p className="text-sm text-muted-foreground">
                  Should be fixed - may cause issues with bank approval
                </p>
              </div>
            </div>
            <div className="flex gap-4 items-start">
              <div className="flex-shrink-0 w-3 h-3 bg-blue-500 rounded-full mt-2"></div>
              <div>
                <h4 className="font-semibold mb-1">Minor Discrepancies</h4>
                <p className="text-sm text-muted-foreground">
                  Optional fixes - improve document quality and compliance
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (stepId === 'exporter-reports') {
    return (
      <div className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-purple-50 rounded-xl mb-4">
            <Download className="w-8 h-8 text-purple-600" />
          </div>
          <h2 className="text-3xl font-bold text-foreground mb-4">Generate Reports</h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Create and download comprehensive validation reports
          </p>
        </div>

        <Card className="border-gray-200/50">
          <CardHeader>
            <CardTitle>Report Features</CardTitle>
            <CardDescription>What's included in your validation reports</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="flex gap-3 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Validation Summary</h4>
                  <p className="text-sm text-muted-foreground">
                    Complete overview of validation results
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <FileCheck className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Discrepancy Details</h4>
                  <p className="text-sm text-muted-foreground">
                    Detailed list of all discrepancies found
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <Download className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Evidence Pack</h4>
                  <p className="text-sm text-muted-foreground">
                    Download all documents and evidence
                  </p>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <FileText className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="font-semibold mb-1">Bank-Ready Format</h4>
                  <p className="text-sm text-muted-foreground">
                    Professional PDF reports ready for submission
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

