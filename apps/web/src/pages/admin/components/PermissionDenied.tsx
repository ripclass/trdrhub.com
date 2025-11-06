import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ShieldAlert, Mail } from 'lucide-react';

export function PermissionDenied({ section }: { section: string }) {
  return (
    <Card className="shadow-soft border-0">
      <CardContent className="p-12 text-center">
        <div className="flex justify-center mb-6">
          <div className="p-4 rounded-full bg-destructive/10">
            <ShieldAlert className="w-12 h-12 text-destructive" />
          </div>
        </div>
        <h3 className="text-2xl font-bold text-foreground mb-2">Access Denied</h3>
        <p className="text-muted-foreground max-w-md mx-auto mb-6">
          You don't have permission to access {section}. Contact your system administrator if you
          believe this is an error.
        </p>
        <Button variant="outline" onClick={() => window.location.href = 'mailto:admin@lcopilot.com'}>
          <Mail className="w-4 h-4 mr-2" />
          Request Access
        </Button>
      </CardContent>
    </Card>
  );
}

