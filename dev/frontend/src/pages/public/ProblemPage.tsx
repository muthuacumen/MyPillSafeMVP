import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { AlertTriangle, Globe2, SearchX } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §4 -- transcribed verbatim. Layout/styling is ours; words are
// not. Copy lives in `public.problem.*` in both locale files.
//
// The two prose blocks that carry an <em> use <Trans> rather than plain t():
// the emphasis is load-bearing ("the handful of medications YOU actually
// take" is the project's whole thesis), and splitting the sentence into
// fragments would make it untranslatable as a sentence.

export default function ProblemPage() {
  const { t } = useTranslation();

  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">{t('common.home')}</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">{t('common.about')}</Link>
            <span>/</span>
            <span className="text-white/80">{t('public.problem.breadcrumb')}</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">{t('public.problem.eyebrow')}</p>
          <h1 className="text-4xl font-bold">{t('public.problem.title')}</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">{t('public.problem.subtitle')}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-navy text-white rounded-2xl p-6">
            <div className="text-4xl font-black mb-1">{t('public.problem.stat1Value')}</div>
            <p className="text-sm text-white/80 leading-relaxed">{t('public.problem.stat1Body')}</p>
            <p className="text-xs text-white/40 mt-3 italic">{t('public.problem.stat1Source')}</p>
          </div>
          <div className="bg-coral text-white rounded-2xl p-6">
            <div className="text-4xl font-black mb-1">{t('public.problem.stat2Value')}</div>
            <p className="text-sm text-white/90 leading-relaxed">{t('public.problem.stat2Body')}</p>
            <p className="text-xs text-white/60 mt-3 italic">{t('public.problem.stat2Source')}</p>
          </div>
        </div>

        {/* The loose-pill moment */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-warning-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">{t('public.problem.loosePillTitle')}</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">{t('public.problem.loosePillBody')}</p>
        </div>

        {/* Why "just identify the pill" fails */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-danger-bg flex items-center justify-center">
              <SearchX className="w-5 h-5 text-danger-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">{t('public.problem.identifyTitle')}</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">
            <Trans i18nKey="public.problem.identifyBody" components={{ em: <em /> }} />
          </p>
        </div>

        {/* Language barrier */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
              <Globe2 className="w-5 h-5 text-teal-600" />
            </div>
            <h2 className="text-xl font-bold text-navy">{t('public.problem.languageTitle')}</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">{t('public.problem.languageBody')}</p>
        </div>

        {/* Closing line */}
        <div className="bg-navy text-white rounded-2xl p-8 text-center">
          <p className="text-lg leading-relaxed">{t('public.problem.closing')}</p>
        </div>

        <AboutNav current="problem" />
      </div>
    </div>
  );
}
