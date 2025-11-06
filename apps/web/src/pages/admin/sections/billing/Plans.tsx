import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { CreditCard, Edit } from 'lucide-react';

const mockPlans = [
  { name: 'Free', price: '$0/mo', users: 1245, revenue: '$0', features: ['Basic validation', '10 docs/month', 'Email support'] },
  { name: 'Professional', price: '$49/mo', users: 856, revenue: '$41,944', features: ['Advanced validation', '100 docs/month', 'Priority support'] },
  { name: 'Enterprise', price: '$299/mo', users: 124, revenue: '$37,076', features: ['Unlimited validation', 'Unlimited docs', '24/7 support', 'Custom integration'] },
];

export function BillingPlans() {
  return (
    <>
      <div>
        <h2 className="text-3xl font-bold text-foreground mb-2">Plans & Pricing</h2>
        <p className="text-muted-foreground">
          Manage subscription plans and pricing tiers
        </p>
      </div>

      <div className="grid md:grid-cols-3 gap-6">
        {mockPlans.map((plan) => (
          <Card key={plan.name} className="shadow-soft border-0">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{plan.name}</span>
                <Badge variant="outline">{plan.users} users</Badge>
              </CardTitle>
              <CardDescription>
                <span className="text-2xl font-bold text-foreground">{plan.price}</span>
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Monthly Revenue</p>
                  <p className="text-lg font-semibold text-foreground">{plan.revenue}</p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground mb-2">Features</p>
                  <ul className="space-y-1">
                    {plan.features.map((feature, idx) => (
                      <li key={idx} className="text-sm text-muted-foreground flex items-center gap-2">
                        <span className="text-success">✓</span> {feature}
                      </li>
                    ))}
                  </ul>
                </div>
                <Button variant="outline" className="w-full">
                  <Edit className="w-4 h-4 mr-2" />
                  Edit Plan
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </>
  );
}

