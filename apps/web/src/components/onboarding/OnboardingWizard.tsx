import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { useOnboarding } from '@/hooks/use-onboarding'
import {
  sortActivitiesByPriority,
  type BusinessActivity,
  type BusinessTier,
} from '@/api/onboarding'

interface OnboardingWizardProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

// Q1 — What does your business do? (multi-select)
//
// Pre-launch scope-down (2026-04-25): only exporter + importer are
// actively sold. Agent (buying-house) and Services (freight forwarder /
// LC consultant) dashboards land post-launch — until then we don't
// offer them in the wizard. The backend Pydantic validator rejects them
// too, so a stale frontend can't sneak them in.
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

// Pre-launch scope-down (2026-04-25): Q3 (tier) was dropped from the
// wizard. Tier doesn't gate any user-facing feature today, so asking
// at signup was a question we didn't act on. We default to 'sme' on
// every new signup; backend keeps the column for forward compat.
const TIER_DEFAULT: BusinessTier = 'sme'

type WizardStep = 1 | 2

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const { status, completeOnboarding } = useOnboarding()
  const [step, setStep] = useState<WizardStep>(1)
  const [activities, setActivities] = useState<BusinessActivity[]>([])
  const [country, setCountry] = useState<string>('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Hydrate from any partial saved state so a user who abandoned the wizard
  // can resume. Reads both the new shape (details.activities / country) and
  // the legacy shape (business_types / company.type) for users who started
  // on the old 5-role wizard before Day 2 landed. Tier hydration was
  // dropped along with Q3 (2026-04-25 scope-down).
  useEffect(() => {
    if (!open || !status) return
    const details = (status.details as Record<string, unknown> | undefined) ?? {}

    const savedActivities = Array.isArray(details.activities)
      ? (details.activities as string[])
      : Array.isArray(details.business_types)
        ? (details.business_types as string[])
        : []
    // Only the actively-sold activities are pre-selectable. Stale 'agent'
    // / 'services' values from old DB rows get filtered out so the user
    // sees an empty list and picks fresh.
    const allowedActivities = new Set<BusinessActivity>(['exporter', 'importer'])
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
    if (step < 2) setStep((step + 1) as WizardStep)
  }

  const goBack = () => {
    setError(null)
    if (step > 1) setStep((step - 1) as WizardStep)
  }

  const submit = async () => {
    if (submitting) return
    setSubmitting(true)
    setError(null)
    try {
      // Sort by canonical priority before persisting so landing-dashboard
      // selection is deterministic across users (exporter > importer; see
      // ACTIVITY_PRIORITY in @/lib/lcopilot/activities).
      await completeOnboarding({
        activities: sortActivitiesByPriority(activities),
        country,
        tier: TIER_DEFAULT,
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
    void submit()
  }

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------

  const progressDots = (
    <div className="flex justify-center gap-2 pb-2">
      {[1, 2].map((n) => (
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
        handleFinish()
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
        <Button type="submit" disabled={submitting || !canAdvance(2)}>
          {submitting ? 'Saving…' : 'Finish'}
        </Button>
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
      </DialogContent>
    </Dialog>
  )
}
