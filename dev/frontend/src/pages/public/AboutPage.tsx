import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { Ruler, ClipboardCheck, BarChart3, TestTube2, ArrowRight } from 'lucide-react';
import AboutNav from '@/components/AboutNav';
import { FIVE_BRAINS } from '@/content/fiveBrains';

// Content pack §2 -- transcribed verbatim. Layout/styling is ours; words are
// not. Copy lives in `public.about.*`; the five-brain copy lives in
// `public.fiveBrains.*` so the per-brain detail pages reuse the same strings
// (see @/content/fiveBrains for why the icon and route stay in code).

const HOW_WE_WORKED = [
  { key: 'measure', icon: Ruler },
  { key: 'prereg', icon: ClipboardCheck },
  { key: 'data', icon: BarChart3 },
  { key: 'test', icon: TestTube2 },
];

export default function AboutPage() {
  const { t } = useTranslation();

  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">{t('common.home')}</Link>
            <span>/</span>
            <span className="text-white/80">{t('public.about.breadcrumb')}</span>
          </nav>
          <h1 className="text-4xl font-bold">{t('public.about.title')}</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">{t('public.about.subtitle')}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* What MyPillSafe Is */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.about.whatTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.about.whatBody')}</p>
        </div>

        {/* Five Brains */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-5">{t('public.about.brainsTitle')}</h2>
          <div className="space-y-4">
            {FIVE_BRAINS.map(({ key, icon: Icon, href }) => (
              <div key={key} className="flex gap-4 items-start bg-light rounded-xl p-5">
                <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
                  <Icon className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-bold text-navy text-sm mb-1">{t(`public.fiveBrains.${key}.title`)}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{t(`public.fiveBrains.${key}.desc`)}</p>
                  {href && (
                    <Link
                      to={href}
                      className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-teal-700 underline min-h-[44px] sm:min-h-0"
                    >
                      {t('public.about.learnMore')} <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Why this architecture */}
        <div className="bg-navy text-white rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-3">{t('public.about.whyTitle')}</h2>
          <p className="text-white/75 leading-relaxed">
            <Trans i18nKey="public.about.whyBody" components={{ em: <em /> }} />
          </p>
        </div>

        {/* How we worked */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">{t('public.about.howTitle')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {HOW_WE_WORKED.map(({ key, icon: Icon }) => (
              <div key={key} className="bg-light rounded-xl p-5 border-l-4 border-teal-500">
                <Icon className="h-5 w-5 text-teal-600 mb-2" />
                <h3 className="font-bold text-navy text-sm mb-1.5">{t(`public.about.how.${key}.title`)}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{t(`public.about.how.${key}.desc`)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scope note */}
        <div className="bg-light border border-slate-200 rounded-2xl p-6 text-center">
          <p className="text-sm text-slate-600">{t('public.about.scopeNote')}</p>
        </div>

        <AboutNav current="about" />
      </div>
    </div>
  );
}
