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

const businessTypeOptions = [
  'Commodities',
  'Manufacturing',
  'Retail',
  'Services',
  'Logistics',
]

const roleOptions = [
  { value: 'exporter', label: 'Exporter' },
  { value: 'importer', label: 'Importer' },
  { value: 'bank_officer', label: 'Bank Officer' },
  { value: 'bank_admin', label: 'Bank Admin' },
]

const isBankRole = (role?: string | null) =>
  role === 'bank_officer' || role === 'bank_admin'

type WizardStep = 'role' | 'company' | 'business' | 'review' | 'complete'

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const { status, updateProgress, isLoading } = useOnboarding()
  const [step, setStep] = useState<WizardStep>('role')
  const [selectedRole, setSelectedRole] = useState<string>('exporter')
  const [companyForm, setCompanyForm] = useState<CompanyPayload>({ name: '', type: '' })
  const [businessTypes, setBusinessTypes] = useState<string[]>([])
  const waitingForApproval = status?.status === 'under_review'

  const determineInitialStep = (): WizardStep => {
    if (!status || !status.role) return 'role'
    if (!status.company_id) return 'company'
    if (isBankRole(status.role)) {
      return status.completed ? 'complete' : waitingForApproval ? 'review' : 'company'
    }
    return status.completed ? 'complete' : 'business'
  }

  useEffect(() => {
    if (!open) return
    const initialStep = determineInitialStep()
    setStep(initialStep)
    if (status?.role) {
      setSelectedRole(status.role)
    }
    if (status?.details) {
      const details = status.details as Record<string, any>
      if (Array.isArray(details.business_types)) {
        setBusinessTypes(details.business_types as string[])
      }
      if (details.company) {
        setCompanyForm({
          name: details.company.name ?? '',
          type: details.company.type ?? '',
          legal_name: details.company.legal_name ?? '',
          registration_number: details.company.registration_number ?? '',
          regulator_id: details.company.regulator_id ?? '',
          country: details.company.country ?? '',
        })
      }
    }
  }, [open, status])

  useEffect(() => {
    if (status?.completed) {
      onComplete()
      onClose()
    }
  }, [status?.completed, onClose, onComplete])

  const handleRoleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    await updateProgress({ role: selectedRole, onboarding_step: 'role' })
    setStep('company')
  }

  const handleCompanySubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!companyForm.name) return
    const payload: CompanyPayload = {
      name: companyForm.name,
      type: companyForm.type,
      legal_name: companyForm.legal_name,
      registration_number: companyForm.registration_number,
      regulator_id: companyForm.regulator_id,
      country: companyForm.country,
    }
    const isBank = isBankRole(selectedRole)
    await updateProgress({
      onboarding_step: isBank ? 'kyc' : 'company',
      company: payload,
      submit_for_review: isBank,
    })
    setStep(isBank ? 'review' : 'business')
  }

  const handleBusinessSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    await updateProgress({
      onboarding_step: 'business',
      business_types: businessTypes,
      complete: true,
    })
    onComplete()
    onClose()
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

    if (step === 'role') {
      return (
        <form onSubmit={handleRoleSubmit} className="space-y-6">
          <div>
            <h2 className="text-xl font-semibold mb-2">Select your role</h2>
            <p className="text-sm text-muted-foreground">
              We will tailor the experience based on your responsibilities.
            </p>
          </div>
          <RadioGroup value={selectedRole} onValueChange={setSelectedRole} className="space-y-3">
            {roleOptions.map((option) => (
              <div key={option.value} className="flex items-center space-x-3 rounded-md border p-3">
                <RadioGroupItem value={option.value} id={`role-${option.value}`} />
                <Label htmlFor={`role-${option.value}`} className="cursor-pointer">
                  {option.label}
                </Label>
              </div>
            ))}
          </RadioGroup>
          <div className="flex justify-end">
            <Button type="submit">Continue</Button>
          </div>
        </form>
      )
    }

    if (step === 'company') {
      const bank = isBankRole(selectedRole)
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
              <Label htmlFor="company-type">Business type</Label>
              <Select
                value={companyForm.type ?? ''}
                onValueChange={(value) => setCompanyForm((prev) => ({ ...prev, type: value }))}
              >
                <SelectTrigger id="company-type">
                  <SelectValue placeholder="Select type" />
                </SelectTrigger>
                <SelectContent>
                  {businessTypeOptions.map((option) => (
                    <SelectItem key={option} value={option}>
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
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

