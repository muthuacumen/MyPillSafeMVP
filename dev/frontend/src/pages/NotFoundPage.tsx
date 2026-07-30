import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Pill, ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center px-6">
      <div className="text-center animate-fade-in">
        <div className="h-20 w-20 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-6">
          <Pill className="h-10 w-10 text-teal-600" />
        </div>
        <h1 className="text-6xl font-extrabold text-slate-900">404</h1>
        <p className="text-xl font-semibold text-slate-700 mt-2">{t('notFound.title')}</p>
        <p className="text-slate-500 mt-3 max-w-sm mx-auto">{t('notFound.body')}</p>
        <Link to="/dashboard" className="inline-flex items-center gap-2 mt-8 btn-primary">
          <ArrowLeft className="h-4 w-4" />
          {t('notFound.back')}
        </Link>
      </div>
    </div>
  );
}
