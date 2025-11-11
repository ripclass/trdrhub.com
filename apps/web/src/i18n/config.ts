/**
 * i18n Configuration
 * Sets up react-i18next for internationalization
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import Backend from 'i18next-http-backend';

i18n
  .use(Backend)
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    fallbackLng: 'en',
    debug: import.meta.env.DEV, // Enable debug in development
    
    interpolation: {
      escapeValue: false, // not needed for react as it escapes by default
    },
    
    detection: {
      order: ['querystring', 'cookie', 'localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json', // Path to your translation files
    },
    
    ns: ['translation'], // Default namespace
    defaultNS: 'translation',
    
    supportedLngs: ['en', 'bn'], // Supported languages
    nonExplicitSupportedLngs: true, // Allow 'en-US' to fallback to 'en'
  });

export default i18n;

