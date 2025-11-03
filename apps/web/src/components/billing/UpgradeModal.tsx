/**
 * UpgradeModal component - handles plan upgrade flow with payment provider selection
 */

import React, { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Separator } from '@/components/ui/separator';
import { Loader2, Check, Crown, Zap, Building, CreditCard, Smartphone } from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  PlanType,
  PaymentProvider,
  PLAN_DEFINITIONS,
  formatCurrency,
  getPlanDisplayName
} from '@/types/billing';
import { useCheckout } from '@/hooks/useBilling';
import type { CompanyBillingInfo, CheckoutRequest } from '@/types/billing';

interface UpgradeModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentBillingInfo: CompanyBillingInfo;
  onSuccess?: () => void;
}

const STRIPE_PRICE_IDS: Record<PlanType, string | undefined> = {
  [PlanType.FREE]: undefined,
  [PlanType.STARTER]: import.meta.env.VITE_STRIPE_PRICE_STARTER as string | undefined,
  [PlanType.PROFESSIONAL]: import.meta.env.VITE_STRIPE_PRICE_PROFESSIONAL as string | undefined,
  [PlanType.ENTERPRISE]: import.meta.env.VITE_STRIPE_PRICE_ENTERPRISE as string | undefined,
};

const PLAN_PRICES_BDT: Record<PlanType, number> = {
  [PlanType.FREE]: 0,
  [PlanType.STARTER]: 15000,
  [PlanType.PROFESSIONAL]: 45000,
  [PlanType.ENTERPRISE]: 0,
};

const stripeSupported = Boolean(
  STRIPE_PRICE_IDS[PlanType.STARTER] ||
  STRIPE_PRICE_IDS[PlanType.PROFESSIONAL] ||
  STRIPE_PRICE_IDS[PlanType.ENTERPRISE]
);

export function UpgradeModal({
  open,
  onOpenChange,
  currentBillingInfo,
  onSuccess
}: UpgradeModalProps) {
  const [selectedPlan, setSelectedPlan] = useState<PlanType | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<PaymentProvider>(PaymentProvider.SSLCOMMERZ);
  const [step, setStep] = useState<'plans' | 'payment' | 'processing'>('plans');

  const checkout = useCheckout();

  const availablePlans = Object.entries(PLAN_DEFINITIONS)
    .filter(([planKey]) => {
      const plan = planKey as PlanType;
      // Don't show current plan or Free plan in upgrade modal
      return plan !== currentBillingInfo.plan && plan !== PlanType.FREE;
    })
    .map(([planKey, planDef]) => ({
      key: planKey as PlanType,
      ...planDef
    }));

  const getPlanIcon = (plan: PlanType) => {
    switch (plan) {
      case PlanType.STARTER:
        return <Zap className="h-5 w-5 text-blue-500" />;
      case PlanType.PROFESSIONAL:
        return <Crown className="h-5 w-5 text-purple-500" />;
      case PlanType.ENTERPRISE:
        return <Building className="h-5 w-5 text-gold-500" />;
      default:
        return <Zap className="h-5 w-5 text-gray-500" />;
    }
  };

  const getPlanColor = (plan: PlanType) => {
    switch (plan) {
      case PlanType.STARTER:
        return 'border-blue-200 bg-blue-50';
      case PlanType.PROFESSIONAL:
        return 'border-purple-200 bg-purple-50';
      case PlanType.ENTERPRISE:
        return 'border-gold-200 bg-gold-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const handlePlanSelect = (plan: PlanType) => {
    setSelectedPlan(plan);
    if (plan === PlanType.ENTERPRISE) {
      // Enterprise requires custom pricing - redirect to contact
      window.open('mailto:sales@lcopilot.com?subject=Enterprise Plan Inquiry', '_blank');
      onOpenChange(false);
    } else {
      setStep('payment');
    }
  };

  const handleCheckout = async () => {
    if (!selectedPlan) return;

    setStep('processing');

    try {
      const payload: CheckoutRequest = {
        plan: selectedPlan,
        provider: selectedProvider,
        return_url: `${window.location.origin}/dashboard/billing?success=true&plan=${selectedPlan}`,
        cancel_url: `${window.location.origin}/dashboard/billing?cancelled=true`,
        metadata: { plan: selectedPlan },
      };

      if (selectedProvider === PaymentProvider.SSLCOMMERZ) {
        Object.assign(payload, {
          amount: PLAN_PRICES_BDT[selectedPlan],
          currency: 'BDT',
        });
      } else if (selectedProvider === PaymentProvider.STRIPE) {
        const priceId = STRIPE_PRICE_IDS[selectedPlan];
        Object.assign(payload, {
          currency: 'USD',
          mode: 'subscription' as const,
          priceId,
          paymentMethodTypes: ['card'],
        });
      }

      await checkout.mutateAsync(payload);

      onSuccess?.();
      onOpenChange(false);
    } catch (error) {
      setStep('payment');
      console.error('Checkout failed:', error);
    }
  };

  const handleBack = () => {
    if (step === 'payment') {
      setStep('plans');
      setSelectedPlan(null);
    } else if (step === 'processing') {
      setStep('payment');
    }
  };

  const renderPlansStep = () => (
    <>
      <DialogHeader>
        <DialogTitle>Upgrade Your Plan</DialogTitle>
        <DialogDescription>
          Choose a plan that fits your validation needs. You can change or cancel anytime.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-4 max-h-96 overflow-y-auto">
        {availablePlans.map((plan) => (
          <Card
            key={plan.key}
            className={cn(
              'cursor-pointer transition-all hover:shadow-md',
              selectedPlan === plan.key ? getPlanColor(plan.key) : 'hover:border-primary'
            )}
            onClick={() => handlePlanSelect(plan.key)}
          >
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  {getPlanIcon(plan.key)}
                  <CardTitle className="text-lg">{plan.name}</CardTitle>
                </div>
                <div className="text-right">
                  <div className="text-lg font-bold">
                    {plan.price > 0 ? formatCurrency(plan.price) : 'Custom'}
                  </div>
                  {plan.price > 0 && (
                    <div className="text-sm text-muted-foreground">/month</div>
                  )}
                </div>
              </div>
              {plan.popular && (
                <Badge className="w-fit">Most Popular</Badge>
              )}
            </CardHeader>

            <CardContent>
              <div className="space-y-3">
                <div className="text-sm text-muted-foreground">
                  {plan.quota ? `${plan.quota.toLocaleString()} validations per month` : 'Unlimited validations'}
                </div>

                <Separator />

                <ul className="space-y-1">
                  {plan.features.map((feature, index) => (
                    <li key={index} className="text-sm flex items-start space-x-2">
                      <Check className="h-3 w-3 text-green-500 mt-0.5 flex-shrink-0" />
                      <span>{feature}</span>
                    </li>
                  ))}
                </ul>

                {plan.key === PlanType.ENTERPRISE && (
                  <div className="pt-2">
                    <Button variant="outline" size="sm" className="w-full">
                      Contact Sales
                    </Button>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );

  const renderPaymentStep = () => (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center space-x-2">
          <span>Payment Method</span>
          {selectedPlan && (
            <Badge variant="secondary">
              {getPlanDisplayName(selectedPlan)}
            </Badge>
          )}
        </DialogTitle>
        <DialogDescription>
          Choose your preferred payment method to complete the upgrade.
        </DialogDescription>
      </DialogHeader>

      <div className="space-y-6">
        {/* Plan summary */}
        {selectedPlan && (
          <div className="p-4 bg-muted rounded-lg">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-medium">{getPlanDisplayName(selectedPlan)}</div>
                <div className="text-sm text-muted-foreground">
                  {PLAN_DEFINITIONS[selectedPlan].quota?.toLocaleString() || 'Unlimited'} validations per month
                </div>
              </div>
              <div className="text-right">
                <div className="text-lg font-bold">
                  {formatCurrency(PLAN_DEFINITIONS[selectedPlan].price)}
                </div>
                <div className="text-sm text-muted-foreground">/month</div>
              </div>
            </div>
          </div>
        )}

        {/* Payment provider selection */}
        <div className="space-y-4">
          <Label className="text-sm font-medium">Select Payment Method</Label>
          <RadioGroup
            value={selectedProvider}
            onValueChange={(value) => setSelectedProvider(value as PaymentProvider)}
            className="space-y-3"
          >
            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <RadioGroupItem value={PaymentProvider.SSLCOMMERZ} id="sslcommerz" />
              <Label htmlFor="sslcommerz" className="flex-1 cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Smartphone className="h-5 w-5 text-green-600" />
                    <div>
                      <div className="font-medium">SSLCommerz</div>
                      <div className="text-sm text-muted-foreground">
                        bKash, Rocket, Nagad, Cards
                      </div>
                    </div>
                  </div>
                  <Badge variant="secondary">Recommended for BD</Badge>
                </div>
              </Label>
            </div>

            <div className="flex items-center space-x-3 p-3 border rounded-lg">
              <RadioGroupItem
                value={PaymentProvider.STRIPE}
                id="stripe"
                disabled={!stripeSupported}
              />
              <Label htmlFor="stripe" className="flex-1 cursor-pointer">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <CreditCard className="h-5 w-5 text-blue-600" />
                    <div>
                      <div className="font-medium">Stripe</div>
                      <div className="text-sm text-muted-foreground">
                        International Cards, PayPal
                      </div>
                    </div>
                  </div>
                  <Badge variant="secondary">Global</Badge>
                </div>
                {!stripeSupported && (
                  <p className="text-xs text-muted-foreground mt-2">
                    Stripe pricing IDs not configured. Add VITE_STRIPE_PRICE_* env values to enable.
                  </p>
                )}
              </Label>
            </div>
          </RadioGroup>
        </div>

        {/* Actions */}
        <div className="flex space-x-2">
          <Button variant="outline" onClick={handleBack} className="flex-1">
            Back
          </Button>
          <Button onClick={handleCheckout} className="flex-1">
            Continue to Payment
          </Button>
        </div>
      </div>
    </>
  );

  const renderProcessingStep = () => (
    <>
      <DialogHeader>
        <DialogTitle>Processing...</DialogTitle>
        <DialogDescription>
          Redirecting you to secure payment gateway...
        </DialogDescription>
      </DialogHeader>

      <div className="flex flex-col items-center space-y-4 py-8">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <div className="text-center space-y-2">
          <div className="font-medium">Setting up your payment</div>
          <div className="text-sm text-muted-foreground">
            You'll be redirected to {selectedProvider === PaymentProvider.SSLCOMMERZ ? 'SSLCommerz' : 'Stripe'} to complete your payment
          </div>
        </div>
      </div>

      <div className="flex justify-center">
        <Button variant="outline" onClick={handleBack} disabled={checkout.isPending}>
          Cancel
        </Button>
      </div>
    </>
  );

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        {step === 'plans' && renderPlansStep()}
        {step === 'payment' && renderPaymentStep()}
        {step === 'processing' && renderProcessingStep()}
      </DialogContent>
    </Dialog>
  );
}

// Quick upgrade button component
interface QuickUpgradeButtonProps {
  currentPlan: PlanType;
  onUpgrade: () => void;
  className?: string;
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

export function QuickUpgradeButton({
  currentPlan,
  onUpgrade,
  className,
  variant = 'default',
  size = 'default'
}: QuickUpgradeButtonProps) {
  const getRecommendedUpgrade = () => {
    switch (currentPlan) {
      case PlanType.FREE:
        return PlanType.STARTER;
      case PlanType.STARTER:
        return PlanType.PROFESSIONAL;
      default:
        return null;
    }
  };

  const recommendedPlan = getRecommendedUpgrade();

  if (!recommendedPlan) {
    return null;
  }

  return (
    <Button
      onClick={onUpgrade}
      variant={variant}
      size={size}
      className={cn('gap-2', className)}
    >
      <Crown className="h-4 w-4" />
      Upgrade to {getPlanDisplayName(recommendedPlan)}
    </Button>
  );
}