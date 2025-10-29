import React from 'react'
import { Link } from 'react-router-dom'
import { FileText, CheckCircle, AlertTriangle, Download, ArrowRight, Shield, Clock } from 'lucide-react'
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"

export default function WelcomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/30">
      <div className="container mx-auto px-4 py-16">
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center w-20 h-20 bg-primary/10 rounded-2xl mb-6">
            <FileText className="w-10 h-10 text-primary" />
          </div>
          <h1 className="text-4xl lg:text-6xl font-bold text-foreground mb-6">
            LC<span className="bg-gradient-primary bg-clip-text text-transparent">opilot</span>
          </h1>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
            AI-powered Letter of Credit validation platform. Avoid costly errors and get bank-ready in minutes.
          </p>
          <div className="flex items-center justify-center gap-6 text-sm text-muted-foreground mb-8">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-green-600" />
              <span>Bank Grade Security</span>
            </div>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-600" />
              <span>5-Minute Validation</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-primary" />
              <span>99.9% Accuracy</span>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6 mb-12">
          <Card className="text-center border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
            <CardHeader className="pb-4">
              <div className="w-16 h-16 bg-blue-50 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-blue-100 transition-colors">
                <FileText className="w-8 h-8 text-blue-600" />
              </div>
              <CardTitle className="text-lg">Upload LC</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="leading-relaxed">
                Upload your Letter of Credit document for AI-powered validation
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
            <CardHeader className="pb-4">
              <div className="w-16 h-16 bg-green-50 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-green-100 transition-colors">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <CardTitle className="text-lg">OCR & Validation</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="leading-relaxed">
                Automated OCR extraction and Fatal Four validation checks
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
            <CardHeader className="pb-4">
              <div className="w-16 h-16 bg-amber-50 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-amber-100 transition-colors">
                <AlertTriangle className="w-8 h-8 text-amber-600" />
              </div>
              <CardTitle className="text-lg">Review Discrepancies</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="leading-relaxed">
                Review identified discrepancies and validation results
              </CardDescription>
            </CardContent>
          </Card>

          <Card className="text-center border-gray-200/50 hover:border-primary/20 transition-all duration-300 hover:shadow-medium group">
            <CardHeader className="pb-4">
              <div className="w-16 h-16 bg-purple-50 rounded-xl flex items-center justify-center mx-auto mb-4 group-hover:bg-purple-100 transition-colors">
                <Download className="w-8 h-8 text-purple-600" />
              </div>
              <CardTitle className="text-lg">Download Report</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription className="leading-relaxed">
                Generate and download PDF validation report
              </CardDescription>
            </CardContent>
          </Card>
        </div>

        <div className="text-center">
          <Button
            className="bg-gradient-primary hover:opacity-90 text-white px-8 py-6 text-lg font-semibold rounded-xl group"
            asChild
          >
            <Link to="/lcopilot/upload" className="flex items-center">
              Start Validation Process
              <ArrowRight className="w-5 h-5 ml-2 group-hover:translate-x-1 transition-transform" />
            </Link>
          </Button>
          <p className="text-sm text-muted-foreground mt-4">
            No credit card required • Free validation for first LC
          </p>
        </div>
      </div>
    </div>
  )
}