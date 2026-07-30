import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { ArrowLeft, Calculator, Layers, ShieldCheck } from 'lucide-react';
import { FIVE_BRAINS } from '@/content/fiveBrains';

/**
 * The third of five per-brain detail pages -- Deterministic Matcher.
 *
 * Same template as `PrescriptionReaderPage`: hero with breadcrumb, white
 * rounded cards, back-to-About. This brain has no numbered pipeline, so the
 * body is three titled cards (the formula, why abstention is the design,
 * why verification beats identification) instead of a step list.
 *
 * The weights, thresholds and rates quoted here are the frozen, evaluated
 * ones -- they are copy, not code, and live in `public.brains.matcher.*` in
 * both locales.
 */

const BRAIN = FIVE_BRAINS[2];

export default function DeterministicMatcherPage() {
  const { t } = useTranslation();
  const Icon = BRAIN.icon;

  return (
    <div className="bg-light min-h-screen page-fade-in">
      {/* 1. Hero */}
      <div className="bg-navy text-white py-14 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex flex-wrap items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">{t('common.home')}</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">{t('common.about')}</Link>
            <span>/</span>
            <span className="text-white/80">{t('public.brains.matcher.breadcrumb')}</span>
          </nav>
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
              <Icon className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-3xl sm:text-4xl font-bold">{t(`public.fiveBrains.${BRAIN.key}.title`)}</h1>
              <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
                {t('public.brains.matcher.heroLead', { desc: t(`public.fiveBrains.${BRAIN.key}.desc`) })}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* 2. What it does */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.matcher.whatTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">
            <Trans i18nKey="public.brains.matcher.whatBody1" components={{ strong: <strong /> }} />
          </p>
          <p className="text-slate-700 leading-relaxed mt-4">{t('public.brains.matcher.whatBody2')}</p>
        </div>

        {/* 3. The formula, in the open */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
              <Calculator className="h-5 w-5 text-navy" />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-navy mb-3">{t('public.brains.matcher.formulaTitle')}</h2>
              <p className="text-slate-700 leading-relaxed">{t('public.brains.matcher.formulaBody')}</p>
            </div>
          </div>
        </div>

        {/* 4. Abstaining is the design */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
              <ShieldCheck className="h-5 w-5 text-navy" />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-navy mb-3">{t('public.brains.matcher.abstainTitle')}</h2>
              <p className="text-slate-700 leading-relaxed">{t('public.brains.matcher.abstainBody')}</p>
            </div>
          </div>
        </div>

        {/* 5. Why not identify against everything */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <div className="flex items-start gap-4">
            <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
              <Layers className="h-5 w-5 text-navy" />
            </div>
            <div className="min-w-0">
              <h2 className="text-2xl font-bold text-navy mb-3">{t('public.brains.matcher.collisionTitle')}</h2>
              <p className="text-slate-700 leading-relaxed">{t('public.brains.matcher.collisionBody')}</p>
            </div>
          </div>

          <div className="mt-5 rounded-xl border-l-4 border-teal-500 bg-light p-5">
            <p className="text-sm text-slate-700 leading-relaxed">{t('public.brains.matcher.frozenNote')}</p>
          </div>
        </div>

        {/* 6. Back to About */}
        <div className="pt-2">
          <Link
            to="/about"
            className="inline-flex items-center justify-center gap-2 border border-navy text-navy py-3 px-6 rounded-xl font-semibold hover:bg-navy hover:text-white transition-colors min-h-[44px]"
          >
            <ArrowLeft className="h-4 w-4 flex-shrink-0" />
            {t('public.brains.backToAbout')}
          </Link>
        </div>
      </div>
    </div>
  );
}
