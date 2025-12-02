import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { OnboardingWizard } from '@/components/onboarding/OnboardingWizard'
import { useOnboarding } from '@/hooks/use-onboarding'
import { getOnboardingStatus } from '@/api/onboarding'

export default function Onboarding() {
  const navigate = useNavigate()
  const { status } = useOnboarding()
  const [wizardOpen, setWizardOpen] = useState(false)

  useEffect(() => {
    // Check if onboarding is already complete
    const checkStatus = async () => {
      try {
        const onboardingStatus = await getOnboardingStatus()
        if (onboardingStatus.completed) {
          // Simplified routing: Banks go to bank dashboard, everyone else to Hub
          const role = onboardingStatus.role
          const destination = (role === 'bank_officer' || role === 'bank_admin')
            ? '/lcopilot/bank-dashboard'
            : '/hub'
          navigate(destination)
        } else {
          // Show wizard
          setWizardOpen(true)
        }
      } catch (error) {
        console.error('Failed to check onboarding status:', error)
        // Show wizard anyway
        setWizardOpen(true)
      }
    }

    checkStatus()
  }, [navigate])

  const handleComplete = () => {
    setWizardOpen(false)
    // Simplified routing: Banks go to bank dashboard, everyone else to Hub
    if (status) {
      const role = status.role
      const destination = (role === 'bank_officer' || role === 'bank_admin')
        ? '/lcopilot/bank-dashboard'
        : '/hub'
      navigate(destination)
    } else {
      // Default to Hub
      navigate('/hub')
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/10 to-primary/5 flex items-center justify-center p-4">
      <OnboardingWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onComplete={handleComplete} />
    </div>
  )
}

