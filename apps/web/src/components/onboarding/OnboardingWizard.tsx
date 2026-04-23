import React, { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useOnboarding } from '@/hooks/use-onboarding'
import type { BusinessActivity, BusinessTier } from '@/api/onboarding'

interface OnboardingWizardProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

// Q1 — What does your business do? (multi-select)
const ACTIVITY_OPTIONS: Array<{ value: BusinessActivity; label: string; description: string }> = [
  {
    value: 'exporter',
    label: 'We export goods',
    description: "We're the seller in letters of credit.",
  },
  {
    value: 'importer',
    label: 'We import goods',
    description: "We're the buyer in letters of credit.",
  },
  {
    value: 'agent',
    label: "We're a sourcing / buying agent",
    description: 'We manage LC paperwork for foreign buyers buying from local manufacturers.',
  },
  {
    value: 'services',
    label: 'We provide trade documentation services',
    description: 'Freight forwarder, customs broker, or LC consultant.',
  },
]

// Q2 — Where is your business primarily based? (drives jurisdiction rule pack)
// ISO 3166-1 alpha-2. Locked list matches the onboarding redesign memory.
// "Other" deferred — users in other countries can pick the closest match and
// update later in settings; backend accepts any valid ISO-2 so extending the
// list is a zero-migration change.
const COUNTRY_OPTIONS: Array<{ code: string; label: string }> = [
  { code: 'BD', label: 'Bangladesh' },
  { code: 'IN', label: 'India' },
  { code: 'PK', label: 'Pakistan' },
  { code: 'VN', label: 'Vietnam' },
  { code: 'LK', label: 'Sri Lanka' },
  { code: 'AE', label: 'United Arab Emirates' },
  { code: 'SA', label: 'Saudi Arabia' },
  { code: 'TR', label: 'Turkey' },
  { code: 'CN', label: 'China' },
  { code: 'HK', label: 'Hong Kong' },
  { code: 'SG', label: 'Singapore' },
  { code: 'GB', label: 'United Kingdom' },
  { code: 'US', label: 'United States' },
  { code: 'DE', label: 'Germany' },
  { code: 'NL', label: 'Netherlands' },
]

// Q3 — How big is your team? (drives pricing tier, NOT dashboard layout)
const TIER_OPTIONS: Array<{ value: BusinessTier; label: string; sublabel: string }> = [
  { value: 'solo', label: 'Solo', sublabel: 'Just me / 1–3 people' },
  { value: 'sme', label: 'SME', sublabel: '4–20 people' },
  {
    value: 'enterprise',
    label: 'Enterprise',
    sublabel: '21+ people, multi-office, need SSO + audit log',
  },
]

const TIER_DEFAULT_ON_SKIP: BusinessTier = 'sme'

type WizardStep = 1 | 2 | 3

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const { status, completeOnboarding } = useOnboarding()
  const [step, setStep] = useState<WizardStep>(1)
  const [activities, setActivities] = useState<BusinessActivity[]>([])
  const [country, setCountry] = useState<string>('')
  const [tier, setTier] = useState<BusinessTier | ''>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Hydrate from any partial saved state so a user who abandoned the wizard
  // can resume. Reads both the new shape (details.activities/country/tier)
  // and the legacy shape (business_types / company.type / company.size) for
  // users who started on the old 5-role wizard before Day 2 landed.
  useEffect(() => {
    if (!open || !status) return
    const details = (status.details as Record<string, unknown> | undefined) ?? {}

    const savedActivities = Array.isArray(details.activities)
      ? (details.activities as string[])
      : Array.isArray(details.business_types)
        ? (details.business_types as string[])
        : []
    const allowedActivities = new Set<BusinessActivity>(['exporter', 'importer', 'agent', 'services'])
    const hydrated = savedActivities.filter((a): a is BusinessActivity =>
      allowedActivities.has(a as BusinessActivity),
    )
    if (hydrated.length > 0) setActivities(hydrated)

    const savedCountry =
      (typeof details.country === 'string' ? (details.country as string) : undefined) ??
      ((details.company as Record<string, unknown> | undefined)?.country as string | undefined)
    if (savedCountry && /^[A-Za-z]{2}$/.test(savedCountry)) {
      setCountry(savedCountry.toUpperCase())
    }

    const savedTier =
      (typeof details.tier === 'string' ? (details.tier as string) : undefined) ??
      ((details.company as Record<string, unknown> | undefined)?.size as string | undefined)
    if (savedTier && (savedTier === 'solo' || savedTier === 'sme' || savedTier === 'enterprise')) {
      setTier(savedTier)
    }
  }, [open, status])

  // Already-onboarded users who somehow hit the wizard — just close.
  useEffect(() => {
    if (!open) return
    if (status?.completed) {
      onComplete()
      onClose()
    }
  }, [status?.completed, onClose, onComplete, open])

  const toggleActivity = (value: BusinessActivity) => {
    setActivities((prev) =>
      prev.includes(value) ? prev.filter((item) => item !== value) : [...prev, value],
    )
  }

  const canAdvance = (from: WizardStep): boolean => {
    if (from === 1) return activities.length > 0
    if (from === 2) return /^[A-Z]{2}$/.test(country)
    return true
  }

  const goNext = () => {
    if (!canAdvance(step)) return
    setError(null)
    if (step < 3) setStep((step + 1) as WizardStep)
  }

  const goBack = () => {
    setError(null)
    if (step > 1) setStep((step - 1) as WizardStep)
  }

  const submit = async (finalTier: BusinessTier) => {
    if (submitting) return
    setSubmitting(true)
    setError(null)
    try {
      await completeOnboarding({
        activities,
        country,
        tier: finalTier,
      })
      onComplete()
      onClose()
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(`Failed to save onboarding: ${message}. Please try again.`)
    } finally {
      setSubmitting(false)
    }
  }

  const handleFinish = () => {
    const finalTier = tier || TIER_DEFAULT_ON_SKIP
    void submit(finalTier)
  }

  const handleSkipTier = () => {
    void submit(TIER_DEFAULT_ON_SKIP)
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const progressDots = (
    <div className="flex justify-center gap-2 pb-2">
      {[1, 2, 3].map((n) => (
        <span
          key={n}
          className={
            'h-2 w-2 rounded-full ' +
            (n === step ? 'bg-primary' : n < step ? 'bg-primary/60' : 'bg-muted')
          }
          aria-hidden
        />
      ))}
    </div>
  )

  const renderStep1 = () => (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault()
        goNext()
      }}
    >
      <div>
        <h2 className="text-xl font-semibold mb-2">What does your business do?</h2>
        <p className="text-sm text-muted-foreground">
          Select all that apply. This determines which dashboards you'll see.
        </p>
      </div>
      <div className="grid gap-3">
        {ACTIVITY_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className="flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-muted/40"
          >
            <Checkbox
              checked={activities.includes(opt.value)}
              onCheckedChange={() => toggleActivity(opt.value)}
              id={`activity-${opt.value}`}
            />
            <span className="flex flex-col">
              <span className="font-medium">{opt.label}</span>
              <span className="text-sm text-muted-foreground">{opt.description}</span>
            </span>
          </label>
        ))}
      </div>
      <div className="flex justify-end gap-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!canAdvance(1)}>
          Continue
        </Button>
      </div>
    </form>
  )

  const renderStep2 = () => (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault()
        goNext()
      }}
    >
      <div>
        <h2 className="text-xl font-semibold mb-2">Where is your business primarily based?</h2>
        <p className="text-sm text-muted-foreground">
          This selects the right country rule pack on top of UCP600 and ISBP821.
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="onboarding-country">Country</Label>
        <Select value={country} onValueChange={setCountry}>
          <SelectTrigger id="onboarding-country">
            <SelectValue placeholder="Select a country" />
          </SelectTrigger>
          <SelectContent>
            {COUNTRY_OPTIONS.map((c) => (
              <SelectItem key={c.code} value={c.code}>
                {c.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <div className="flex justify-between gap-2">
        <Button type="button" variant="ghost" onClick={goBack}>
          Back
        </Button>
        <Button type="submit" disabled={!canAdvance(2)}>
          Continue
        </Button>
      </div>
    </form>
  )

  const renderStep3 = () => (
    <form
      className="space-y-6"
      onSubmit={(e) => {
        e.preventDefault()
        handleFinish()
      }}
    >
      <div>
        <h2 className="text-xl font-semibold mb-2">How big is your team that touches LCs?</h2>
        <p className="text-sm text-muted-foreground">
          Drives pricing tier and enterprise features. You can change this later.
        </p>
      </div>
      <RadioGroup
        value={tier}
        onValueChange={(v) => setTier(v as BusinessTier)}
        className="space-y-3"
      >
        {TIER_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className="flex cursor-pointer items-start gap-3 rounded-md border p-3 hover:bg-muted/40"
            htmlFor={`tier-${opt.value}`}
          >
            <RadioGroupItem value={opt.value} id={`tier-${opt.value}`} />
            <span className="flex flex-col">
              <span className="font-medium">{opt.label}</span>
              <span className="text-sm text-muted-foreground">{opt.sublabel}</span>
            </span>
          </label>
        ))}
      </RadioGroup>
      {error && (
        <Alert variant="destructive">
          <AlertTitle>Couldn't save</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
      <div className="flex justify-between gap-2">
        <Button type="button" variant="ghost" onClick={goBack} disabled={submitting}>
          Back
        </Button>
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={handleSkipTier} disabled={submitting}>
            Skip (use SME)
          </Button>
          <Button type="submit" disabled={submitting}>
            {submitting ? 'Saving…' : 'Finish'}
          </Button>
        </div>
      </div>
    </form>
  )

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Welcome to trdrhub</DialogTitle>
        </DialogHeader>
        {progressDots}
        {step === 1 && renderStep1()}
        {step === 2 && renderStep2()}
        {step === 3 && renderStep3()}
      </DialogContent>
    </Dialog>
  )
}
