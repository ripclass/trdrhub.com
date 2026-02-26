import React, { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Package, Eye, EyeOff } from 'lucide-react';
import { useExporterAuth } from '@/lib/exporter/auth';

export default function ExporterLogin() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');

  const { login } = useExporterAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    try {
      // If user entered demo credentials, allow direct demo access without auth backend dependency
      const isDemoCredential = demoCredentials.some(
        (cred) => cred.email.toLowerCase() === email.trim().toLowerCase() && cred.password === password
      );

      if (isDemoCredential) {
        localStorage.setItem('demo_mode', 'true');
        window.location.href = '/lcopilot/exporter-dashboard?demo=true';
        return;
      }

      await login(email, password);
      // Ensure deterministic redirect after successful login
      window.location.href = '/lcopilot/exporter-dashboard';
    } catch (err) {
      const raw = err instanceof Error ? err.message : 'Login failed';
      if (/invalid login credentials|invalid_credentials|email or password/i.test(raw)) {
        setError('Login failed. If this is a demo attempt, use the demo credentials and click Sign in, or use Enter Demo Mode.');
      } else {
        setError(raw);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const demoCredentials = [
    { role: 'Exporter', email: 'exporter1@globalexports.com', password: 'exporter123' },
    { role: 'Exporter', email: 'exporter2@globalexports.com', password: 'exporter123' },
    { role: 'Tenant Admin', email: 'admin@globalexports.com', password: 'admin123' },
    { role: 'Tenant Admin', email: 'manager@globalexports.com', password: 'manager123' },
  ];

  const fillCredentials = (email: string, password: string) => {
    setEmail(email);
    setPassword(password);
  };

  const handleDemoMode = () => {
    localStorage.setItem('demo_mode', 'true');
    window.location.href = '/lcopilot/exporter-dashboard?demo=true';
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        {/* Header */}
        <div className="text-center">
          <Package className="mx-auto h-12 w-12 text-green-600" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Exporter Dashboard
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Sign in to access LCopilot Exporter Dashboard
          </p>
        </div>

        {/* Login Form */}
        <Card>
          <CardHeader>
            <CardTitle>Sign In</CardTitle>
            <CardDescription>
              Enter your exporter credentials to continue
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
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
                  placeholder="exporter1@globalexports.com"
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
                disabled={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Demo Mode Button */}
        <Card className="border-green-200 bg-green-50">
          <CardContent className="pt-6">
            <Button
              onClick={handleDemoMode}
              className="w-full bg-green-600 hover:bg-green-700"
              variant="default"
            >
              🚀 Enter Demo Mode (No Login Required)
            </Button>
            <p className="text-xs text-gray-600 mt-2 text-center">
              Access dashboard without authentication for demo purposes
            </p>
          </CardContent>
        </Card>

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
          <p>LCopilot Exporter Dashboard v1.0</p>
          <p className="mt-1">For authorized exporter users only</p>
        </div>
      </div>
    </div>
  );
}

