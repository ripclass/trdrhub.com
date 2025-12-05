import React from 'react';
import { toast } from 'sonner';

import { Button } from '@/components/ui/button';

type ErrorBoundaryProps = {
  children: React.ReactNode;
};

type ErrorBoundaryState = {
  hasError: boolean;
  message?: string;
};

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, message: error.message ?? 'Unexpected application error' };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('Unhandled UI error', error, info);
    toast.error('Something went wrong', {
      description: error.message ?? 'Please try again shortly.',
    });
  }

  private handleRetry = () => {
    this.setState({ hasError: false, message: undefined });
  };

  private handleGoToHub = () => {
    window.location.href = '/hub';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
          <div>
            <h1 className="text-2xl font-semibold">Something went wrong</h1>
            <p className="text-muted-foreground mt-2 max-w-md">
              {this.state.message ?? 'An unexpected error occurred. Please try again.'}
            </p>
          </div>
          <div className="flex gap-2">
            <Button onClick={this.handleGoToHub}>Go to Hub</Button>
            <Button variant="outline" onClick={this.handleRetry}>
              Try again
            </Button>
            <Button variant="ghost" onClick={() => window.location.reload()}>
              Reload
            </Button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
