import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { ArrowLeft, Inbox, Languages, RefreshCw } from 'lucide-react';
import { FIVE_BRAINS } from '@/content/fiveBrains';

/**
 * The fifth of five per-brain detail pages -- Answer Voice.
 *
 * Same template as `PrescriptionReaderPage`: hero with breadcrumb, white
 * rounded cards, a three-step "how it works" list on bg-light rows, and the
 * back-to-About button.
 *
 * The celecoxib section gets the amber warning treatment because it is a
 * recorded failure, not a feature: it is the measurement that moved
 * generation to a stronger model and added the claim-vs-source check.
 */

const BRAIN = FIVE_BRAINS[4];

const HOW_IT_WORKS = [
  { key: 'receive', icon: Inbox },
  { key: 'phrase', icon: Languages },
  { key: 'recheck', icon: RefreshCw },
];

export default function AnswerVoicePage() {
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
            <span className="text-white/80">{t('public.brains.voice.breadcrumb')}</span>
          </nav>
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
              <Icon className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-3xl sm:text-4xl font-bold">{t(`public.fiveBrains.${BRAIN.key}.title`)}</h1>
              <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
                {t('public.brains.voice.heroLead', { desc: t(`public.fiveBrains.${BRAIN.key}.desc`) })}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* 2. What it does */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.voice.whatTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.voice.whatBody1')}</p>
          <p className="text-slate-700 leading-relaxed mt-4">
            <Trans i18nKey="public.brains.voice.whatBody2" components={{ strong: <strong /> }} />
          </p>
        </div>

        {/* 3. The failure that shaped it */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.voice.storyTitle')}</h2>
          <div className="bg-warning-bg border border-warning-border rounded-xl p-5">
            <p className="text-sm text-warning-text leading-relaxed">{t('public.brains.voice.storyBody')}</p>
          </div>
        </div>

        {/* 4. How it works */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-5">{t('public.brains.voice.howTitle')}</h2>
          <div className="space-y-4">
            {HOW_IT_WORKS.map(({ key, icon: StepIcon }) => (
              <div key={key} className="flex gap-4 items-start bg-light rounded-xl p-5">
                <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
                  <StepIcon className="h-5 w-5 text-navy" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-navy text-sm mb-1">{t(`public.brains.voice.how.${key}.title`)}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{t(`public.brains.voice.how.${key}.body`)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 5. Measured, honestly */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.voice.measuredTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.voice.measuredBody')}</p>
          <p className="text-xs text-slate-500 leading-relaxed mt-5 border-t border-slate-100 pt-4">
            {t('public.brains.voice.measuredNote')}
          </p>
        </div>

        {/* 6. Privacy -- what is and is not sent to the cloud. The claim was
            code-verified against cb4_service.py/qa.py (red-team check D,
            2026-07-30): the API call carries the system prompt, the packed
            monograph passages, and the question text -- never the profile,
            DIN set, name, DOB, or user id. If that call site changes, this
            copy must be re-verified. */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.voice.privacyTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.voice.privacyBody')}</p>
        </div>

        {/* 7. Back to About */}
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
