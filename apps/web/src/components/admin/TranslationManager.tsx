import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, CheckCircle, AlertCircle, RefreshCw, Languages } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface PendingTranslation {
  key: string;
  value: string;
  context?: string;
}

interface TranslationStatus {
  supported_languages: string[];
  total_languages: number;
  pending_counts: Record<string, number>;
}

export function TranslationManager() {
  const { t } = useTranslation();
  const { toast } = useToast();

  const [isLoading, setIsLoading] = useState(false);
  const [status, setStatus] = useState<TranslationStatus | null>(null);
  const [selectedLanguage, setSelectedLanguage] = useState<string>('bn');
  const [pendingTranslations, setPendingTranslations] = useState<PendingTranslation[]>([]);
  const [editingKey, setEditingKey] = useState<string>('');
  const [editingValue, setEditingValue] = useState<string>('');

  useEffect(() => {
    fetchTranslationStatus();
  }, []);

  useEffect(() => {
    if (selectedLanguage) {
      fetchPendingTranslations(selectedLanguage);
    }
  }, [selectedLanguage]);

  const fetchTranslationStatus = async () => {
    try {
      const response = await fetch('/api/translations/status');
      if (response.ok) {
        const data = await response.json();
        setStatus(data);
      }
    } catch (error) {
      toast({
        title: t('errors.translationError'),
        description: 'Failed to fetch translation status',
        variant: 'destructive',
      });
    }
  };

  const fetchPendingTranslations = async (language: string) => {
    setIsLoading(true);
    try {
      const response = await fetch(`/api/translations/pending?language=${language}`);
      if (response.ok) {
        const data = await response.json();
        setPendingTranslations(flattenTranslations(data.pending));
      }
    } catch (error) {
      toast({
        title: t('errors.translationError'),
        description: 'Failed to fetch pending translations',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const flattenTranslations = (obj: any, prefix = ''): PendingTranslation[] => {
    const result: PendingTranslation[] = [];
    for (const [key, value] of Object.entries(obj)) {
      const fullKey = prefix ? `${prefix}.${key}` : key;
      if (typeof value === 'object' && value !== null && !key.startsWith('_')) {
        result.push(...flattenTranslations(value, fullKey));
      } else if (typeof value === 'string') {
        result.push({ key: fullKey, value: value as string });
      }
    }
    return result;
  };

  const generateTranslations = async (language: string) => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/translations/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          target_language: language,
          force_regenerate: false,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        toast({
          title: t('common.success'),
          description: `Generated ${data.generated_count} translations for ${language}`,
        });
        fetchPendingTranslations(language);
        fetchTranslationStatus();
      } else {
        throw new Error('Failed to generate translations');
      }
    } catch (error) {
      toast({
        title: t('errors.translationError'),
        description: 'Failed to generate translations',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const verifyTranslation = async (key: string, value: string) => {
    try {
      const response = await fetch('/api/translations/verify', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          language: selectedLanguage,
          key,
          verified_value: value,
        }),
      });

      if (response.ok) {
        toast({
          title: t('common.success'),
          description: `Translation verified for ${key}`,
        });
        fetchPendingTranslations(selectedLanguage);
        setEditingKey('');
        setEditingValue('');
      } else {
        throw new Error('Failed to verify translation');
      }
    } catch (error) {
      toast({
        title: t('errors.translationError'),
        description: 'Failed to verify translation',
        variant: 'destructive',
      });
    }
  };

  const clearCache = async () => {
    try {
      const response = await fetch('/api/translations/cache/clear', {
        method: 'POST',
      });

      if (response.ok) {
        toast({
          title: t('common.success'),
          description: 'Translation cache cleared',
        });
      } else {
        throw new Error('Failed to clear cache');
      }
    } catch (error) {
      toast({
        title: t('errors.translationError'),
        description: 'Failed to clear cache',
        variant: 'destructive',
      });
    }
  };

  if (!status) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('admin.translations')}</h1>
          <p className="text-muted-foreground">
            Manage AI-assisted translations and human verification
          </p>
        </div>
        <Button onClick={clearCache} variant="outline" size="sm">
          <RefreshCw className="h-4 w-4 mr-2" />
          {t('admin.clearCache')}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Supported Languages
            </CardTitle>
            <Languages className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{status.total_languages}</div>
            <p className="text-xs text-muted-foreground">
              {status.supported_languages.join(', ')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Pending Translations
            </CardTitle>
            <AlertCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Object.values(status.pending_counts).reduce((a, b) => a + b, 0)}
            </div>
            <p className="text-xs text-muted-foreground">
              Across all languages
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Translation Status
            </CardTitle>
            <CheckCircle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(status.pending_counts).map(([lang, count]) => (
                <div key={lang} className="flex justify-between text-sm">
                  <span>{lang.toUpperCase()}</span>
                  <Badge variant={count > 0 ? 'destructive' : 'default'}>
                    {count}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <Tabs defaultValue="manage" className="space-y-4">
        <TabsList>
          <TabsTrigger value="manage">Manage Translations</TabsTrigger>
          <TabsTrigger value="generate">Generate Translations</TabsTrigger>
        </TabsList>

        <TabsContent value="generate" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('admin.generateTranslations')}</CardTitle>
              <CardDescription>
                Generate AI-assisted translations for missing keys
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                {status.supported_languages
                  .filter(lang => lang !== 'en')
                  .map(language => (
                    <Button
                      key={language}
                      onClick={() => generateTranslations(language)}
                      disabled={isLoading}
                      variant="outline"
                      className="justify-between"
                    >
                      <span>Generate {language.toUpperCase()}</span>
                      <Badge variant="secondary">
                        {status.pending_counts[language] || 0} pending
                      </Badge>
                    </Button>
                  ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="manage" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('admin.pendingTranslations')}</CardTitle>
              <CardDescription>
                Review and verify AI-generated translations
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center space-x-4">
                <Label htmlFor="language-select">Language:</Label>
                <Select value={selectedLanguage} onValueChange={setSelectedLanguage}>
                  <SelectTrigger id="language-select" className="w-32">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {status.supported_languages
                      .filter(lang => lang !== 'en')
                      .map(language => (
                        <SelectItem key={language} value={language}>
                          {language.toUpperCase()}
                        </SelectItem>
                      ))}
                  </SelectContent>
                </Select>
              </div>

              {isLoading ? (
                <div className="flex items-center justify-center p-8">
                  <Loader2 className="h-8 w-8 animate-spin" />
                </div>
              ) : pendingTranslations.length === 0 ? (
                <Alert>
                  <CheckCircle className="h-4 w-4" />
                  <AlertDescription>
                    No pending translations for {selectedLanguage.toUpperCase()}
                  </AlertDescription>
                </Alert>
              ) : (
                <div className="space-y-4">
                  {pendingTranslations.map((translation) => (
                    <Card key={translation.key}>
                      <CardContent className="pt-4">
                        <div className="space-y-3">
                          <div>
                            <Label className="text-sm font-medium">Key:</Label>
                            <p className="text-sm text-muted-foreground font-mono">
                              {translation.key}
                            </p>
                          </div>

                          <div>
                            <Label htmlFor={`translation-${translation.key}`}>
                              Translation:
                            </Label>
                            {editingKey === translation.key ? (
                              <div className="space-y-2">
                                <Textarea
                                  value={editingValue}
                                  onChange={(e) => setEditingValue(e.target.value)}
                                  className="min-h-[80px]"
                                />
                                <div className="flex space-x-2">
                                  <Button
                                    size="sm"
                                    onClick={() => verifyTranslation(translation.key, editingValue)}
                                  >
                                    {t('admin.verifyTranslation')}
                                  </Button>
                                  <Button
                                    size="sm"
                                    variant="outline"
                                    onClick={() => {
                                      setEditingKey('');
                                      setEditingValue('');
                                    }}
                                  >
                                    {t('common.cancel')}
                                  </Button>
                                </div>
                              </div>
                            ) : (
                              <div className="space-y-2">
                                <p className="text-sm p-3 bg-muted rounded border">
                                  {translation.value}
                                </p>
                                <Button
                                  size="sm"
                                  variant="outline"
                                  onClick={() => {
                                    setEditingKey(translation.key);
                                    setEditingValue(translation.value);
                                  }}
                                >
                                  {t('common.edit')}
                                </Button>
                              </div>
                            )}
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}