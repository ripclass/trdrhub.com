import React, { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Download, FileText, Languages, AlertCircle } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';

interface ReportDownloadDialogProps {
  sessionId: string;
  children?: React.ReactNode;
}

type ReportMode = 'single' | 'bilingual' | 'parallel';

export function ReportDownloadDialog({ sessionId, children }: ReportDownloadDialogProps) {
  const { t, i18n } = useTranslation();
  const { toast } = useToast();

  const [isOpen, setIsOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [reportMode, setReportMode] = useState<ReportMode>('bilingual');
  const [selectedLanguages, setSelectedLanguages] = useState<string[]>(['en']);
  const [forceRegenerate, setForceRegenerate] = useState(false);

  const availableLanguages = [
    { code: 'en', name: 'English', nativeName: 'English' },
    { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
    { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
  ];

  const handleLanguageChange = (languageCode: string, checked: boolean) => {
    if (checked) {
      setSelectedLanguages([...selectedLanguages, languageCode]);
    } else {
      setSelectedLanguages(selectedLanguages.filter(lang => lang !== languageCode));
    }
  };

  const downloadReport = async () => {
    if (selectedLanguages.length === 0) {
      toast({
        title: t('errors.validationFailed'),
        description: 'Please select at least one language',
        variant: 'destructive',
      });
      return;
    }

    setIsDownloading(true);

    try {
      const languageParam = selectedLanguages.join(',');
      const url = `/api/sessions/${sessionId}/report?languages=${languageParam}&report_mode=${reportMode}&regenerate=${forceRegenerate}`;

      const response = await fetch(url);

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      // Create a temporary link to download the file
      const link = document.createElement('a');
      link.href = data.download_url;
      link.download = `lc_report_${sessionId}_${languageParam}_${reportMode}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

      toast({
        title: t('common.success'),
        description: 'Report downloaded successfully',
      });

      setIsOpen(false);
    } catch (error) {
      console.error('Download failed:', error);
      toast({
        title: t('errors.reportGenerationFailed'),
        description: 'Failed to download report. Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsDownloading(false);
    }
  };

  const getReportModeDescription = (mode: ReportMode) => {
    switch (mode) {
      case 'single':
        return 'Generate report in selected language only';
      case 'bilingual':
        return 'Side-by-side layout with English and local language';
      case 'parallel':
        return 'Separate pages for each selected language';
      default:
        return '';
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        {children || (
          <Button variant="outline" size="sm">
            <Download className="h-4 w-4 mr-2" />
            {t('sessions.downloadReport')}
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-[525px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            {t('reports.title')}
          </DialogTitle>
          <DialogDescription>
            Configure language settings and download options for your validation report.
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* Language Selection */}
          <div className="space-y-3">
            <Label className="text-base font-medium flex items-center gap-2">
              <Languages className="h-4 w-4" />
              {t('reports.language')}
            </Label>
            <div className="grid grid-cols-1 gap-3">
              {availableLanguages.map((language) => (
                <div key={language.code} className="flex items-center space-x-2">
                  <Checkbox
                    id={`lang-${language.code}`}
                    checked={selectedLanguages.includes(language.code)}
                    onCheckedChange={(checked) =>
                      handleLanguageChange(language.code, checked as boolean)
                    }
                  />
                  <Label
                    htmlFor={`lang-${language.code}`}
                    className="text-sm font-normal cursor-pointer flex-1"
                  >
                    <span className="font-medium">{language.name}</span>
                    <span className="text-muted-foreground ml-2">
                      ({language.nativeName})
                    </span>
                  </Label>
                </div>
              ))}
            </div>
          </div>

          {/* Report Mode Selection */}
          {selectedLanguages.length > 1 && (
            <div className="space-y-3">
              <Label className="text-base font-medium">
                {t('reports.reportMode')}
              </Label>
              <RadioGroup value={reportMode} onValueChange={(value) => setReportMode(value as ReportMode)}>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="bilingual" id="bilingual" />
                  <Label htmlFor="bilingual" className="cursor-pointer">
                    <div>
                      <div className="font-medium">{t('reports.bilingual')}</div>
                      <div className="text-sm text-muted-foreground">
                        {getReportModeDescription('bilingual')}
                      </div>
                    </div>
                  </Label>
                </div>
                <div className="flex items-center space-x-2">
                  <RadioGroupItem value="parallel" id="parallel" />
                  <Label htmlFor="parallel" className="cursor-pointer">
                    <div>
                      <div className="font-medium">{t('reports.parallel')}</div>
                      <div className="text-sm text-muted-foreground">
                        {getReportModeDescription('parallel')}
                      </div>
                    </div>
                  </Label>
                </div>
              </RadioGroup>
            </div>
          )}

          {/* Advanced Options */}
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <Checkbox
                id="regenerate"
                checked={forceRegenerate}
                onCheckedChange={(checked) => setForceRegenerate(checked as boolean)}
              />
              <Label htmlFor="regenerate" className="text-sm cursor-pointer">
                {t('reports.regenerate')}
              </Label>
            </div>
            {forceRegenerate && (
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription className="text-sm">
                  This will regenerate the report with current language settings.
                  Generation may take a few moments.
                </AlertDescription>
              </Alert>
            )}
          </div>

          {/* Language Warning */}
          {selectedLanguages.length === 0 && (
            <Alert>
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                Please select at least one language to generate the report.
              </AlertDescription>
            </Alert>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            {t('common.cancel')}
          </Button>
          <Button
            onClick={downloadReport}
            disabled={isDownloading || selectedLanguages.length === 0}
          >
            {isDownloading ? (
              <>
                <div className="h-4 w-4 mr-2 animate-spin rounded-full border-2 border-background border-t-foreground" />
                Generating...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                {t('common.download')}
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}