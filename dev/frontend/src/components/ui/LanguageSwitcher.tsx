import { useTranslation } from 'react-i18next';
import { Globe } from 'lucide-react';

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const isFr = i18n.language === 'fr';

  const toggle = () => {
    const next = isFr ? 'en' : 'fr';
    i18n.changeLanguage(next);
    localStorage.setItem('pillsafe-lang', next);
  };

  return (
    <button
      onClick={toggle}
      title={isFr ? 'Switch to English' : 'Passer en français'}
      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 hover:text-slate-900 text-xs font-semibold transition-colors"
    >
      <Globe className="h-3.5 w-3.5" />
      {isFr ? 'EN' : 'FR'}
    </button>
  );
}
