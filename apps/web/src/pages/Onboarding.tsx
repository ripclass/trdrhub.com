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
          // Redirect to appropriate dashboard
          const role = onboardingStatus.role
          const details = onboardingStatus.details as Record<string, any> | undefined
          const businessTypes = Array.isArray(details?.business_types) ? details.business_types : []
          const hasBoth = businessTypes.includes('exporter') && businessTypes.includes('importer')
          const companySize = details?.company?.size

          let destination = '/lcopilot/exporter-dashboard'
          if (role === 'bank_officer' || role === 'bank_admin') {
            destination = '/lcopilot/bank-dashboard'
          } else if (role === 'tenant_admin') {
            destination = '/lcopilot/enterprise-dashboard'
          } else if (hasBoth && companySize === 'sme') {
            destination = '/lcopilot/combined-dashboard'
          } else if (role === 'importer') {
            destination = '/lcopilot/importer-dashboard'
          }

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
    // Redirect to appropriate dashboard after completion
    if (status) {
      const role = status.role
      const details = status.details as Record<string, any> | undefined
      const businessTypes = Array.isArray(details?.business_types) ? details.business_types : []
      const hasBoth = businessTypes.includes('exporter') && businessTypes.includes('importer')
      const companySize = details?.company?.size

      let destination = '/lcopilot/exporter-dashboard'
      if (role === 'bank_officer' || role === 'bank_admin') {
        destination = '/lcopilot/bank-dashboard'
      } else if (role === 'tenant_admin') {
        destination = '/lcopilot/enterprise-dashboard'
      } else if (hasBoth && companySize === 'sme') {
        destination = '/lcopilot/combined-dashboard'
      } else if (role === 'importer') {
        destination = '/lcopilot/importer-dashboard'
      }

      navigate(destination)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-secondary/10 to-primary/5 flex items-center justify-center p-4">
      <OnboardingWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onComplete={handleComplete} />
    </div>
  )
}

