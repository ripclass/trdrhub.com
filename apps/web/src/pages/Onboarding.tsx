import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard'

export default function Onboarding() {
  const navigate = useNavigate()
  const [wizardOpen, setWizardOpen] = useState(true)

  const handleComplete = () => {
    setWizardOpen(false)
    navigate('/lcopilot/dashboard', { replace: true })
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/10 to-primary/5 flex items-center justify-center p-4">
      <OnboardingWizard
        open={wizardOpen}
        onClose={() => navigate('/lcopilot/dashboard', { replace: true })}
        onComplete={handleComplete}
      />
    </div>
  )
}
