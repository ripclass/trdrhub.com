import { AlertTriangle, Clock } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";

interface RateLimitNoticeProps {
  onRetry?: () => void;
  onCancel?: () => void;
}

export function RateLimitNotice({ onRetry, onCancel }: RateLimitNoticeProps) {
  return (
    <Card className="border-warning/20 bg-warning/5">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-warning">
          <AlertTriangle className="w-5 h-5" />
          Rate Limit Exceeded
        </CardTitle>
        <CardDescription>
          You've reached the maximum number of validation requests for your account.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-start gap-3 p-3 bg-background rounded-lg border">
          <Clock className="w-5 h-5 text-muted-foreground mt-0.5" />
          <div className="space-y-1">
            <p className="text-sm font-medium">Please wait before trying again</p>
            <p className="text-xs text-muted-foreground">
              Free accounts can process up to 5 documents per hour. Upgrade to Pro for unlimited processing.
            </p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <Button variant="outline" onClick={onCancel} className="flex-1">
            Go Back
          </Button>
          <Button onClick={onRetry} className="flex-1">
            Retry Now
          </Button>
        </div>

        <div className="text-center pt-2">
          <Button variant="link" className="text-sm text-primary">
            Upgrade to Pro →
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}