import React from 'react';
import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Button } from '@/components/ui/button';

const languages = [
  { code: 'en', name: 'English', nativeName: 'English' },
  { code: 'bn', name: 'Bengali', nativeName: 'বাংলা' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية' },
];

export function LanguageSelector() {
  const { i18n, t } = useTranslation();

  const currentLanguage = languages.find(lang => lang.code === i18n.language) || languages[0];

  const changeLanguage = (languageCode: string) => {
    i18n.changeLanguage(languageCode);

    // Store language preference
    localStorage.setItem('lcopilot-language', languageCode);

    // Update document direction for RTL languages
    document.documentElement.dir = languageCode === 'ar' ? 'rtl' : 'ltr';
    document.documentElement.lang = languageCode;
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="sm" className="h-8 w-8 px-0">
          <Globe className="h-4 w-4" />
          <span className="sr-only">Select language</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-48">
        {languages.map((language) => (
          <DropdownMenuItem
            key={language.code}
            onClick={() => changeLanguage(language.code)}
            className={`flex justify-between ${
              currentLanguage.code === language.code ? 'bg-accent' : ''
            }`}
          >
            <span>{language.name}</span>
            <span className="text-muted-foreground text-sm">
              {language.nativeName}
            </span>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export default LanguageSelector;