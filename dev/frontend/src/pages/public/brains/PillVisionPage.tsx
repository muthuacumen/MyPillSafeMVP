import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { ArrowLeft, Eye, Palette, Shapes, Type } from 'lucide-react';
import { FIVE_BRAINS } from '@/content/fiveBrains';
import trayRender from '@/assets/pillsafe-tray-render.jpg';

/**
 * The second of five per-brain detail pages -- Pill Vision.
 *
 * Structure and visual language are cloned from `PrescriptionReaderPage`
 * (hero with breadcrumb / white rounded cards / bg-light step rows /
 * back-to-About button), which is the template for the whole `brains/`
 * folder. Two conventions it inherits: the page lives OFF the About chain
 * (reached from the About page's Five Brains card, not `ABOUT_PAGES`), and
 * it is fully translated EN/FR.
 *
 * ONE DELIBERATE DIFFERENCE from the template: the measured stat VALUES are
 * NOT code constants here. `31.1%` renders as `31,1 %` in French, so the
 * value is language and lives in the locale files beside its label --
 * unlike `PrescriptionReaderPage`'s `MEASURED_ROWS`, whose counts
 * ("12 of 12") are locale-identical and therefore stay in code.
 *
 * Every number on this page is measured and traceable to the project's
 * evaluation documentation. The tray section carries no accuracy claim --
 * the confirmatory capture study has not run -- and this page must never
 * claim "100% accuracy".
 */

const BRAIN = FIVE_BRAINS[1];

const HOW_IT_WORKS = [
  { key: 'find', icon: Eye },
  { key: 'colour', icon: Palette },
  { key: 'shape', icon: Shapes },
  { key: 'imprint', icon: Type },
];

// Only the stat KEYS are structure; both the value and the label beneath it
// are locale-formatted copy (see the header note).
const STAT_KEYS = ['detect', 'verify', 'fa'] as const;

const PENDING_KEYS = ['p1', 'p2', 'p3', 'p4', 'p5'] as const;

// Re-encoded from the 2.4 MB design render (JPEG q85, max width 1400 px).
// The intrinsic size is declared on the <img> so the card reserves its space
// before the lazy-loaded file arrives.
const TRAY_IMAGE_WIDTH = 1400;
const TRAY_IMAGE_HEIGHT = 933;

export default function PillVisionPage() {
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
            <span className="text-white/80">{t('public.brains.vision.breadcrumb')}</span>
          </nav>
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
              <Icon className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-3xl sm:text-4xl font-bold">{t(`public.fiveBrains.${BRAIN.key}.title`)}</h1>
              <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
                {t('public.brains.vision.heroLead', { desc: t(`public.fiveBrains.${BRAIN.key}.desc`) })}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* 2. What it does */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.vision.whatTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.vision.whatBody1')}</p>
          <p className="text-slate-700 leading-relaxed mt-4">
            <Trans i18nKey="public.brains.vision.whatBody2" components={{ strong: <strong /> }} />
          </p>
        </div>

        {/* 3. How it works */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-5">{t('public.brains.vision.howTitle')}</h2>
          <div className="space-y-4">
            {HOW_IT_WORKS.map(({ key, icon: StepIcon }) => (
              <div key={key} className="flex gap-4 items-start bg-light rounded-xl p-5">
                <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
                  <StepIcon className="h-5 w-5 text-navy" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-navy text-sm mb-1">{t(`public.brains.vision.how.${key}.title`)}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{t(`public.brains.vision.how.${key}.body`)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 4. Measured performance */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.vision.measuredTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.vision.measuredIntro')}</p>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-5">
            {STAT_KEYS.map((key) => (
              <div key={key} className="bg-light border-l-4 border-teal-500 rounded-r-xl p-5">
                <p className="text-2xl font-bold text-navy leading-tight">
                  {t(`public.brains.vision.stats.${key}.value`)}
                </p>
                <p className="text-xs text-slate-600 leading-relaxed mt-2">
                  {t(`public.brains.vision.stats.${key}.label`)}
                </p>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-xl border-l-4 border-teal-500 bg-light p-5">
            <p className="text-sm text-slate-700 leading-relaxed">{t('public.brains.vision.measuredNote')}</p>
          </div>
        </div>

        {/* 5. The negative finding */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.vision.negativeTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.vision.negativeBody')}</p>
        </div>

        {/* 6. The PillSafeTray */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <h2 className="text-2xl font-bold text-navy">{t('public.brains.vision.trayTitle')}</h2>
            <span className="inline-flex items-center bg-warning-bg text-warning-text border border-warning-border text-[11px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full">
              {t('public.brains.vision.trayBadge')}
            </span>
          </div>

          <p className="text-slate-700 leading-relaxed">{t('public.brains.vision.trayBody1')}</p>
          <p className="text-slate-700 leading-relaxed mt-4">{t('public.brains.vision.trayBody2')}</p>

          <figure className="mt-6">
            <img
              src={trayRender}
              alt={t('public.brains.vision.trayImageAlt')}
              width={TRAY_IMAGE_WIDTH}
              height={TRAY_IMAGE_HEIGHT}
              loading="lazy"
              className="w-full h-auto rounded-xl border border-slate-100 bg-light"
            />
            <figcaption className="text-xs text-slate-500 leading-relaxed mt-3">
              {t('public.brains.vision.trayImageCaption')}
            </figcaption>
          </figure>
        </div>

        {/* 7. Pending work */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.vision.pendingTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.vision.pendingIntro')}</p>
          <ol className="mt-5 space-y-3">
            {PENDING_KEYS.map((key, i) => (
              <li key={key} className="flex items-start gap-3">
                <span className="flex-shrink-0 w-7 h-7 bg-navy/10 rounded-full text-xs flex items-center justify-center font-bold text-navy">
                  {i + 1}
                </span>
                <p className="text-sm text-slate-700 leading-relaxed">{t(`public.brains.vision.pending.${key}`)}</p>
              </li>
            ))}
          </ol>
        </div>

        {/* 8. Back to About */}
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
