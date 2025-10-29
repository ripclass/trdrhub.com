import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';
import LanguageDetector from 'i18next-browser-languagedetector';

// Import translation resources
import enTranslations from './locales/en.json';
import bnTranslations from './locales/bn.json';
import arTranslations from './locales/ar.json';

const resources = {
  en: { translation: enTranslations },
  bn: { translation: bnTranslations },
  ar: { translation: arTranslations }
};

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    debug: import.meta.env.DEV,

    interpolation: {
      escapeValue: false, // React already does escaping
    },

    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      lookupLocalStorage: 'lcopilot-language',
      caches: ['localStorage'],
    },

    backend: {
      loadPath: '/api/translations/{{lng}}',
      crossDomain: true,
    },

    react: {
      useSuspense: false,
    },
  });

export default i18n;