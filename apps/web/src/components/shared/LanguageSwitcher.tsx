/**
 * Language Switcher Component
 * Allows users to switch between available languages
 */
import * as React from "react";
import { useTranslation } from "react-i18next";
import { Globe } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const languages = [
  { code: "en", name: "English", nativeName: "English" },
  { code: "bn", name: "Bangla", nativeName: "বাংলা" },
];

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();
  const currentLang = languages.find((lang) => lang.code === i18n.language) || languages[0];

  const handleLanguageChange = (langCode: string) => {
    i18n.changeLanguage(langCode);
    // Persist to localStorage (handled by i18next-browser-languagedetector)
    localStorage.setItem("i18nextLng", langCode);
    // Update URL if on bank dashboard
    if (typeof window !== "undefined") {
      const url = new URL(window.location.href);
      url.searchParams.set("lang", langCode);
      window.history.replaceState({}, "", url);
    }
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" className="gap-2">
          <Globe className="h-4 w-4" />
          <span className="max-w-[80px] truncate">{currentLang.nativeName}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        {languages.map((lang) => (
          <DropdownMenuItem
            key={lang.code}
            onClick={() => handleLanguageChange(lang.code)}
            className={i18n.language === lang.code ? "bg-accent" : ""}
          >
            <span className="font-medium">{lang.nativeName}</span>
            {i18n.language === lang.code && (
              <Badge variant="secondary" className="ml-2 text-xs">
                ✓
              </Badge>
            )}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

