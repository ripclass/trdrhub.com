import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Building2, Eye, EyeOff, Shield } from 'lucide-react';
import { useBankAuth } from '@/lib/bank/auth';
import { bankAuthApi } from '@/api/bank';

export default function BankLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  
  // 2FA state
  const [showPasswordStep, setShowPasswordStep] = useState(true);
  const [show2FAStep, setShow2FAStep] = useState(false);
  const [twoFACode, setTwoFACode] = useState('');
  const [twoFASessionId, setTwoFASessionId] = useState('');
  const [isRequesting2FA, setIsRequesting2FA] = useState(false);
  const [isVerifying2FA, setIsVerifying2FA] = useState(false);
  const [twoFAError, setTwoFAError] = useState('');

  const { login } = useBankAuth();

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      // First, authenticate with password
      await login(email, password);
      
      // Check if 2FA is enabled (try to request code)
      try {
        setIsRequesting2FA(true);
        const response = await bankAuthApi.request2FA();
        setTwoFASessionId(response.session_id);
        setShowPasswordStep(false);
        setShow2FAStep(true);
        
        // In development, show the code
        if (response.code) {
          console.log('2FA Code (dev only):', response.code);
        }
      } catch (err: any) {
        // If 2FA is not enabled (501), proceed with normal login
        if (err?.response?.status === 501) {
          // 2FA not enabled, login complete
          // Navigation handled by login method
        } else {
          // Other error - show but don't block login
          console.warn('2FA request failed:', err);
          // Login still succeeds, just without 2FA
        }
      } finally {
        setIsRequesting2FA(false);
        setIsLoading(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
      setIsLoading(false);
    }
  };

  const handle2FASubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsVerifying2FA(true);
    setTwoFAError('');

    try {
      await bankAuthApi.verify2FA(twoFACode, twoFASessionId);
      // 2FA verified - navigation already handled by login method
      // The login method should have already navigated
    } catch (err: any) {
      setTwoFAError(err?.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setIsVerifying2FA(false);
    }
  };

  const handleResend2FA = async () => {
    setIsRequesting2FA(true);
    setTwoFAError('');
    try {
      const response = await bankAuthApi.request2FA();
      setTwoFASessionId(response.session_id);
      if (response.code) {
        console.log('2FA Code (dev only):', response.code);
      }
    } catch (err: any) {
      setTwoFAError(err?.response?.data?.detail || 'Failed to resend code');
    } finally {
      setIsRequesting2FA(false);
    }
  };

  const demoCredentials = [
    { role: 'Bank Admin', email: 'admin@bankone.com', password: 'admin123' },
    { role: 'Bank Admin', email: 'manager@bankone.com', password: 'manager123' },
    { role: 'Bank Officer', email: 'officer1@bankone.com', password: 'officer123' },
    { role: 'Bank Officer', email: 'officer2@bankone.com', password: 'officer123' },
    { role: 'Bank Officer', email: 'officer3@bankone.com', password: 'officer123' },
  ];

  const fillCredentials = (email: string, password: string) => {
    setEmail(email);
    setPassword(password);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Building2 className="mx-auto h-12 w-12 text-blue-600" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Bank Dashboard
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to access LCopilot Bank Dashboard
          </p>
        </div>

        {/* Password Login Form */}
        {showPasswordStep && (
          <Card>
            <CardHeader>
              <CardTitle>Sign In</CardTitle>
              <CardDescription>
                Enter your bank credentials to continue
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <Label htmlFor="email">Email</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@bankone.com"
                />
              </div>

              <div>
                <Label htmlFor="password">Password</Label>
                <div className="relative">
                  <Input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Enter your password"
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-0 pr-3 flex items-center"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? (
                      <EyeOff className="h-4 w-4 text-gray-400" />
                    ) : (
                      <Eye className="h-4 w-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              {error && (
                <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
                  {error}
                </div>
              )}

                <Button
                  type="submit"
                  className="w-full"
                  disabled={isLoading || isRequesting2FA}
                >
                  {isLoading || isRequesting2FA ? 'Signing in...' : 'Sign in'}
                </Button>
              </form>
            </CardContent>
          </Card>
        )}

        {/* 2FA Verification Form */}
        {show2FAStep && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="h-5 w-5" />
                Two-Factor Authentication
              </CardTitle>
              <CardDescription>
                Enter the 6-digit code sent to your registered device
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handle2FASubmit} className="space-y-4">
                <div>
                  <Label htmlFor="2fa-code">Verification Code</Label>
                  <Input
                    id="2fa-code"
                    name="2fa-code"
                    type="text"
                    inputMode="numeric"
                    maxLength={6}
                    required
                    value={twoFACode}
                    onChange={(e) => {
                      const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                      setTwoFACode(value);
                    }}
                    placeholder="000000"
                    className="text-center text-2xl tracking-widest font-mono"
                    autoFocus
                  />
                  <p className="text-xs text-muted-foreground mt-2">
                    Enter the 6-digit code from your authenticator app or SMS
                  </p>
                </div>

                {twoFAError && (
                  <div className="text-red-600 text-sm bg-red-50 p-3 rounded-md">
                    {twoFAError}
                  </div>
                )}

                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="flex-1"
                    onClick={() => {
                      setShow2FAStep(false);
                      setShowPasswordStep(true);
                      setTwoFACode('');
                      setTwoFAError('');
                    }}
                    disabled={isVerifying2FA}
                  >
                    Back
                  </Button>
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={handleResend2FA}
                    disabled={isRequesting2FA || isVerifying2FA}
                    className="text-sm"
                  >
                    {isRequesting2FA ? 'Sending...' : 'Resend Code'}
                  </Button>
                  <Button
                    type="submit"
                    className="flex-1"
                    disabled={twoFACode.length !== 6 || isVerifying2FA}
                  >
                    {isVerifying2FA ? 'Verifying...' : 'Verify'}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        )}

        {/* Demo Credentials */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Demo Credentials</CardTitle>
            <CardDescription>
              Click any credential set to auto-fill the form
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {demoCredentials.map((cred, index) => (
                <button
                  key={index}
                  onClick={() => fillCredentials(cred.email, cred.password)}
                  className="w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors"
                >
                  <div className="font-medium text-gray-900">{cred.role}</div>
                  <div className="text-sm text-gray-600">{cred.email}</div>
                  <div className="text-xs text-gray-500">Password: {cred.password}</div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Footer */}
        <div className="text-center text-sm text-gray-500">
          <p>LCopilot Bank Dashboard v1.0</p>
          <p className="mt-1">For authorized bank personnel only</p>
        </div>
      </div>
    </div>
  );
}

