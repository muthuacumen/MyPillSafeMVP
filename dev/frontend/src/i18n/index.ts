import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import fr from './locales/fr.json';

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: localStorage.getItem('pillsafe-lang') ?? 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
});

// Keep <html lang> in step with the active language. Without this the
// document stayed lang="en" after switching to French, so a screen reader
// announced French medication copy with an English voice -- and
// French-speaking seniors are a primary user group for this app. Driven by
// the languageChanged event rather than the switcher component so every
// caller of changeLanguage() is covered, including the initial value above.
const syncDocumentLanguage = (lng: string) => {
  document.documentElement.lang = lng.split('-')[0];
};

syncDocumentLanguage(i18n.language);
i18n.on('languageChanged', syncDocumentLanguage);

export default i18n;
