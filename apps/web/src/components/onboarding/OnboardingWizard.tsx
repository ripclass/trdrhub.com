import React, { useEffect, useMemo, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useOnboarding } from '@/hooks/use-onboarding'
import type { CompanyPayload } from '@/api/onboarding'

interface OnboardingWizardProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

const COMPANY_TYPES = [
  { value: 'exporter', label: 'Exporter' },
  { value: 'importer', label: 'Importer' },
  { value: 'both', label: 'Both Exporter & Importer' },
  { value: 'bank', label: 'Bank' },
]

const COMPANY_SIZE_OPTIONS = [
  { value: 'sme', label: 'SME (1-20 employees)' },
  { value: 'medium', label: 'Medium Enterprise (21-50 employees)' },
  { value: 'large', label: 'Large Enterprise (50+ employees)' },
]

const businessTypeOptions = [
  'Commodities',
  'Manufacturing',
  'Retail',
  'Services',
  'Logistics',
]

const isBankRole = (role?: string | null) =>
  role === 'bank_officer' || role === 'bank_admin'

const getBackendRole = (companyType: string, size?: string): string => {
  if (companyType === 'both') {
    if (size === 'medium' || size === 'large') {
      return 'tenant_admin'
    }
    return 'exporter'
  }

  const roleMap: Record<string, string> = {
    exporter: 'exporter',
    importer: 'importer',
    bank: 'bank_officer',
  }

  return roleMap[companyType] || 'exporter'
}

type WizardStep = 'company_type' | 'company_size' | 'company' | 'business' | 'review' | 'complete'

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const { status, updateProgress, isLoading } = useOnboarding()
  const [step, setStep] = useState<WizardStep>('company_type')
  const [companyType, setCompanyType] = useState<string>('')
  const [companySize, setCompanySize] = useState<string>('')
  const [contactPerson, setContactPerson] = useState<string>('')
  const [companyForm, setCompanyForm] = useState<CompanyPayload>({ name: '', type: '' })
  const [businessTypes, setBusinessTypes] = useState<string[]>([])
  const waitingForApproval = status?.status === 'under_review'

  const determineInitialStep = (): WizardStep => {
    if (!status) return 'company_type'
    const details = status.details as Record<string, any> | undefined
    const hasCompanyType = details?.company?.type
    const hasCompanySize = details?.company?.size
    const hasCompanyName = status.company_id || details?.company?.name
    
    if (!hasCompanyType) return 'company_type'
    if (hasCompanyType === 'both' && !hasCompanySize) return 'company_size'
    if (!hasCompanyName) return 'company'
    
    const backendRole = status.role || getBackendRole(hasCompanyType, hasCompanySize)
    if (isBankRole(backendRole)) {
      return status.completed ? 'complete' : waitingForApproval ? 'review' : 'company'
    }
    return status.completed ? 'complete' : 'business'
  }

  useEffect(() => {
    if (!open) return
    const initialStep = determineInitialStep()
    setStep(initialStep)
    
    if (status?.details) {
      const details = status.details as Record<string, any>
      if (details.company) {
        setCompanyType(details.company.type ?? '')
        setCompanySize(details.company.size ?? '')
        setContactPerson(details.contact_person ?? '')
        setCompanyForm({
          name: details.company.name ?? '',
          type: details.company.type ?? '',
          legal_name: details.company.legal_name ?? '',
          registration_number: details.company.registration_number ?? '',
          regulator_id: details.company.regulator_id ?? '',
          country: details.company.country ?? '',
        })
      }
      if (Array.isArray(details.business_types)) {
        setBusinessTypes(details.business_types as string[])
      }
    }
  }, [open, status])

  useEffect(() => {
    if (status?.completed) {
      onComplete()
      onClose()
    }
  }, [status?.completed, onClose, onComplete])

  const handleCompanyTypeSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!companyType) return
    
    const backendRole = getBackendRole(companyType, companySize)
    const businessTypes = companyType === 'both' ? ['exporter', 'importer'] : [companyType]
    
    await updateProgress({
      role: backendRole,
      company: { type: companyType, size: companySize },
      business_types: businessTypes,
      onboarding_step: companyType === 'both' && !companySize ? 'company_size' : 'company',
    })
    
    if (companyType === 'both' && !companySize) {
      setStep('company_size')
    } else {
      setStep('company')
    }
  }

  const handleCompanySizeSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!companySize) return
    
    const backendRole = getBackendRole(companyType, companySize)
    const businessTypes = ['exporter', 'importer']
    
    await updateProgress({
      role: backendRole,
      company: { type: companyType, size: companySize },
      business_types: businessTypes,
      onboarding_step: 'company',
    })
    
    setStep('company')
  }

  const handleCompanySubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!companyForm.name) return
    
    const backendRole = getBackendRole(companyType, companySize)
    const isBank = isBankRole(backendRole)
    const requiresTeamSetup = backendRole === 'tenant_admin'
    
    const payload: CompanyPayload = {
      name: companyForm.name,
      type: companyType,
      size: companySize || undefined,
      legal_name: companyForm.legal_name,
      registration_number: companyForm.registration_number,
      regulator_id: companyForm.regulator_id,
      country: companyForm.country,
    }
    
    await updateProgress({
      role: backendRole,
      onboarding_step: isBank ? 'kyc' : requiresTeamSetup ? 'team_setup' : 'company',
      company: payload,
      contact_person: contactPerson,
      submit_for_review: isBank,
      complete: !(isBank || requiresTeamSetup),
    })
    
    setStep(isBank ? 'review' : 'business')
  }

  const handleBusinessSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    
    try {
      // Ensure we include company data when completing onboarding
      // This is critical because company data might have been saved in earlier steps
      const backendRole = getBackendRole(companyType, companySize)
      const companyPayload: CompanyPayload | undefined = companyForm.name ? {
        name: companyForm.name,
        type: companyType,
        size: companySize || undefined,
        legal_name: companyForm.legal_name,
        registration_number: companyForm.registration_number,
        regulator_id: companyForm.regulator_id,
        country: companyForm.country,
      } : undefined
      
      const finalBusinessTypes = businessTypes.length > 0 
        ? businessTypes 
        : (companyType === 'both' ? ['exporter', 'importer'] : companyType ? [companyType] : [])
      
      console.log('💾 Saving onboarding data:', {
        role: backendRole,
        company: companyPayload,
        business_types: finalBusinessTypes,
        companyType,
        companySize
      })
      
      const result = await updateProgress({
        role: backendRole,
        onboarding_step: 'business',
        business_types: finalBusinessTypes,
        company: companyPayload,
        contact_person: contactPerson,
        complete: true,
      })
      
      console.log('✅ Onboarding saved successfully:', {
        completed: result.completed,
        company_id: result.company_id,
        details: result.details
      })
      
      onComplete()
      onClose()
    } catch (error: any) {
      console.error('❌ Failed to save onboarding:', error)
      alert(`Failed to save onboarding: ${error?.message || 'Unknown error'}. Please try again.`)
      // Don't close modal on error - let user retry
    }
  }

  const toggleBusinessType = (value: string) => {
    setBusinessTypes((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value]
    )
  }

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="py-16 text-center text-muted-foreground">
          Loading onboarding...
        </div>
      )
    }

    if (!status && !open) {
      return null
    }

    if (step === 'company_type') {
      return (
        <form onSubmit={handleCompanyTypeSubmit} className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">What type of company are you?</h2>
            <p className="text-sm text-muted-foreground">
              Select the option that best describes your business. This helps us tailor your workspace.
            </p>
          </div>
          <RadioGroup value={companyType} onValueChange={setCompanyType} className="space-y-3">
            {COMPANY_TYPES.map((option) => (
              <div key={option.value} className="flex items-center space-x-3 rounded-md border p-3">
                <RadioGroupItem value={option.value} id={`company-type-${option.value}`} />
                <Label htmlFor={`company-type-${option.value}`} className="cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
          <div className="flex justify-end">
            <Button type="submit" disabled={!companyType}>Continue</Button>
          </div>
        </form>
      )
    }

    if (step === 'company_size') {
      return (
        <form onSubmit={handleCompanySizeSubmit} className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">What's your company size?</h2>
            <p className="text-sm text-muted-foreground">
              We use this to tailor features, quotas, and onboarding for your organization.
            </p>
          </div>
          <RadioGroup value={companySize} onValueChange={setCompanySize} className="space-y-3">
            {COMPANY_SIZE_OPTIONS.map((option) => (
              <div key={option.value} className="flex items-center space-x-3 rounded-md border p-3">
                <RadioGroupItem value={option.value} id={`company-size-${option.value}`} />
                <Label htmlFor={`company-size-${option.value}`} className="cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
          <div className="flex justify-end">
            <Button type="submit" disabled={!companySize}>Continue</Button>
          </div>
        </form>
      )
    }

    if (step === 'company') {
      const backendRole = getBackendRole(companyType, companySize)
      const bank = isBankRole(backendRole)
      return (
        <form onSubmit={handleCompanySubmit} className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">Company details</h2>
            <p className="text-sm text-muted-foreground">
              Tell us about your organisation. This helps us configure the right experience.
            </p>
          </div>
          <div className="space-y-4">
            <div>
              <Label htmlFor="company-name">Company name</Label>
              <Input
                id="company-name"
                value={companyForm.name}
                onChange={(e) => setCompanyForm((prev) => ({ ...prev, name: e.target.value }))}
                required
              />
            </div>
            <div>
              <Label htmlFor="contact-person">Contact person</Label>
              <Input
                id="contact-person"
                value={contactPerson}
                onChange={(e) => setContactPerson(e.target.value)}
                placeholder="Your full name"
                required
              />
            </div>
            {bank && (
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <Label htmlFor="legal-name">Legal entity name</Label>
                  <Input
                    id="legal-name"
                    value={companyForm.legal_name ?? ''}
                    onChange={(e) => setCompanyForm((prev) => ({ ...prev, legal_name: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="registration-number">Registration number</Label>
                  <Input
                    id="registration-number"
                    value={companyForm.registration_number ?? ''}
                    onChange={(e) =>
                      setCompanyForm((prev) => ({ ...prev, registration_number: e.target.value }))
                    }
                    required
                  />
                </div>
                <div>
                  <Label htmlFor="regulator">Regulator</Label>
                  <Input
                    id="regulator"
                    value={companyForm.regulator_id ?? ''}
                    onChange={(e) => setCompanyForm((prev) => ({ ...prev, regulator_id: e.target.value }))}
                  />
                </div>
                <div>
                  <Label htmlFor="country">Country</Label>
                  <Input
                    id="country"
                    value={companyForm.country ?? ''}
                    onChange={(e) => setCompanyForm((prev) => ({ ...prev, country: e.target.value }))}
                    required
                  />
                </div>
              </div>
            )}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Continue</Button>
          </div>
        </form>
      )
    }

    if (step === 'business') {
      return (
        <form onSubmit={handleBusinessSubmit} className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">What best describes your business?</h2>
            <p className="text-sm text-muted-foreground">
              Select all that apply. We use this to tailor dashboards and guidance.
            </p>
          </div>
          <div className="grid gap-3">
            {businessTypeOptions.map((option) => (
              <label key={option} className="flex items-center space-x-3 rounded-md border p-3">
                <Checkbox
                  checked={businessTypes.includes(option)}
                  onCheckedChange={() => toggleBusinessType(option)}
                />
                <span>{option}</span>
              </label>
            ))}
          </div>
          <div className="flex justify-end gap-2">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit">Finish onboarding</Button>
          </div>
        </form>
      )
    }

    if (step === 'review') {
      return (
        <div className="space-y-6">
          <Alert>
            <AlertTitle>Submitted for review</AlertTitle>
            <AlertDescription>
              Your bank onboarding details have been submitted. Our team will verify the information
              and notify you once approval is complete. You can close this window for now.
            </AlertDescription>
          </Alert>
          <div className="flex justify-end">
            <Button onClick={onClose}>Close</Button>
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        <h2 className="text-xl font-semibold">Onboarding complete</h2>
        <p className="text-muted-foreground">
          You can now explore the full platform. If you ever want to revisit onboarding guidance,
          you can access it from the settings menu.
        </p>
        <div className="flex justify-end">
          <Button onClick={onClose}>Close</Button>
        </div>
      </div>
    )
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Welcome to trdrhub</DialogTitle>
        </DialogHeader>
        {renderContent()}
      </DialogContent>
    </Dialog>
  )
}

