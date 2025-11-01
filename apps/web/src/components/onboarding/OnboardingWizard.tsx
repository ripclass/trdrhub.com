import React, { useState, useEffect } from 'react'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { useOnboarding } from '@/hooks/use-onboarding'
import { getOnboardingContent, type OnboardingContent, type OnboardingStep } from '@/api/onboarding'
import { WelcomeStep } from './steps/WelcomeStep'
import { RoleIntroductionStep } from './steps/RoleIntroductionStep'
import { PlatformOverviewStep } from './steps/PlatformOverviewStep'
import { ExporterOnboardingSteps } from './steps/role-specific/ExporterOnboardingSteps'
import { ImporterOnboardingSteps } from './steps/role-specific/ImporterOnboardingSteps'
import { BankOnboardingSteps } from './steps/role-specific/BankOnboardingSteps'
import { AdminOnboardingSteps } from './steps/role-specific/AdminOnboardingSteps'
import { ArrowLeft, ArrowRight, X } from 'lucide-react'

interface OnboardingWizardProps {
  open: boolean
  onClose: () => void
  onComplete: () => void
}

export function OnboardingWizard({ open, onClose, onComplete }: OnboardingWizardProps) {
  const { status, updateProgress, markComplete } = useOnboarding()
  const [content, setContent] = useState<OnboardingContent | null>(null)
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadContent = async () => {
      if (!status?.role) return

      try {
        setIsLoading(true)
        const onboardingContent = await getOnboardingContent(status.role)
        setContent(onboardingContent)
        
        // Set current step from progress if available
        if (status.current_progress?.current_step) {
          const stepIndex = onboardingContent.steps.findIndex(
            (s) => s.step_id === status.current_progress?.current_step
          )
          if (stepIndex >= 0) {
            setCurrentStepIndex(stepIndex)
          }
        }
      } catch (error) {
        console.error('Failed to load onboarding content:', error)
      } finally {
        setIsLoading(false)
      }
    }

    if (open && status) {
      loadContent()
    }
  }, [open, status])

  const currentStep = content?.steps[currentStepIndex]
  const totalSteps = content?.steps.length || 0
  const progress = totalSteps > 0 ? ((currentStepIndex + 1) / totalSteps) * 100 : 0

  const handleNext = async () => {
    if (!currentStep || !content) return

    // Mark current step as completed
    await updateProgress({
      current_step: currentStep.step_id,
      completed_steps: [currentStep.step_id],
    })

    if (currentStepIndex < totalSteps - 1) {
      setCurrentStepIndex(currentStepIndex + 1)
      // Update progress with new current step
      const nextStep = content.steps[currentStepIndex + 1]
      await updateProgress({
        current_step: nextStep.step_id,
      })
    } else {
      // Completed all steps
      await markComplete(true)
      onComplete()
    }
  }

  const handlePrevious = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1)
    }
  }

  const handleSkip = async () => {
    if (!currentStep) return

    // Mark current step as skipped
    await updateProgress({
      skipped_steps: [currentStep.step_id],
    })

    if (currentStepIndex < totalSteps - 1) {
      setCurrentStepIndex(currentStepIndex + 1)
      const nextStep = content?.steps[currentStepIndex + 1]
      if (nextStep) {
        await updateProgress({
          current_step: nextStep.step_id,
        })
      }
    } else {
      await markComplete(true)
      onComplete()
    }
  }

  const handleSkipAll = async () => {
    if (!content) return

    // Mark all remaining steps as skipped
    const remainingSteps = content.steps.slice(currentStepIndex).map((s) => s.step_id)
    await updateProgress({
      skipped_steps: remainingSteps,
    })
    await markComplete(true)
    onComplete()
  }

  const renderStep = () => {
    if (!currentStep || !content) return null

    const stepId = currentStep.step_id

    // Base steps
    if (stepId === 'welcome') {
      return <WelcomeStep welcomeMessage={content.welcome_message} />
    }

    if (stepId === 'role-introduction') {
      return (
        <RoleIntroductionStep
          role={content.role}
          introduction={content.introduction}
          keyFeatures={content.key_features}
        />
      )
    }

    if (stepId === 'platform-overview') {
      return <PlatformOverviewStep role={content.role} />
    }

    // Role-specific steps
    const role = content.role
    if (role === 'exporter') {
      return <ExporterOnboardingSteps stepId={stepId} onNext={handleNext} />
    }
    if (role === 'importer') {
      return <ImporterOnboardingSteps stepId={stepId} onNext={handleNext} />
    }
    if (role === 'bank_officer' || role === 'bank_admin') {
      return <BankOnboardingSteps stepId={stepId} onNext={handleNext} />
    }
    if (role === 'system_admin') {
      return <AdminOnboardingSteps stepId={stepId} onNext={handleNext} />
    }

    // Generic fallback
    return (
      <div className="space-y-6">
        <div className="text-center">
          <h2 className="text-3xl font-bold text-foreground mb-4">{currentStep.title}</h2>
          {currentStep.description && (
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              {currentStep.description}
            </p>
          )}
        </div>
      </div>
    )
  }

  if (isLoading) {
    return (
      <Dialog open={open} onOpenChange={onClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-center py-12">
            <div className="animate-spin w-8 h-8 border-2 border-primary border-t-transparent rounded-full mr-3"></div>
            <span className="text-muted-foreground">Loading onboarding...</span>
          </div>
        </DialogContent>
      </Dialog>
    )
  }

  if (!content || !currentStep) {
    return null
  }

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between mb-4">
            <DialogTitle className="text-2xl">Get Started</DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="h-8 w-8 p-0"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
          <DialogDescription>
            Step {currentStepIndex + 1} of {totalSteps}
          </DialogDescription>
        </DialogHeader>

        {/* Progress Bar */}
        <div className="mb-6">
          <Progress value={progress} className="h-2" />
        </div>

        {/* Step Content */}
        <div className="min-h-[400px] py-6">
          {renderStep()}
        </div>

        {/* Navigation */}
        <div className="flex items-center justify-between pt-6 border-t">
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={handlePrevious}
              disabled={currentStepIndex === 0}
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Previous
            </Button>
            <Button variant="ghost" onClick={handleSkipAll}>
              Skip All
            </Button>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={handleSkip}>
              Skip
            </Button>
            <Button onClick={handleNext} className="bg-gradient-primary hover:opacity-90">
              {currentStepIndex === totalSteps - 1 ? 'Complete' : 'Next'}
              <ArrowRight className="w-4 h-4 ml-2" />
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

