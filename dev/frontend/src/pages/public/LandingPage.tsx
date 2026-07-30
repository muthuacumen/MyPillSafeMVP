import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import {
  ScanLine, CheckCircle2, Languages, ArrowRight,
  AlertTriangle, XCircle, SearchX, ShieldCheck,
} from 'lucide-react';
import { Logo } from '@/components/ui/Logo';

// Content pack §1 -- transcribed verbatim. Layout/styling is ours; words are
// not. Copy lives in `public.landing.*` in both locale files; what stays here
// is the icon, the step number, and the colour classes per outcome.
//
// The SCIENCE_STRIP `title` values are bibliographic (a challenge name, a
// paper, a published report) and are NOT translated -- only the venue label
// and the explanatory point are, under `public.landing.science.*`.

const HOW_IT_WORKS = [
  { key: 'scan', step: '01', icon: ScanLine },
  { key: 'confirm', step: '02', icon: CheckCircle2 },
  { key: 'verify', step: '03', icon: ShieldCheck },
  { key: 'ask', step: '04', icon: Languages },
];

const OUTCOMES = [
  { key: 'verified', icon: CheckCircle2, classes: 'bg-success-bg border-success-border text-success-text' },
  { key: 'closer', icon: AlertTriangle, classes: 'bg-warning-bg border-warning-border text-warning-text' },
  { key: 'noMatch', icon: XCircle, classes: 'bg-danger-bg border-danger-border text-danger-text' },
  { key: 'nothing', icon: SearchX, classes: 'bg-navy/5 border-navy/20 text-navy' },
];

const SCIENCE_STRIP = [
  { key: 'nlm', title: 'NLM Pill Image Recognition Challenge (2016)' },
  { key: 'epillid', title: 'ePillID (Usuyama et al., 2020)' },
  { key: 'gopill', title: 'GO-PILL (2026)' },
  { key: 'cihi', title: 'CIHI — Drug Use Among Seniors in Canada' },
];

export default function LandingPage() {
  const { t } = useTranslation();

  return (
    <div className="page-fade-in">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-brand-hero text-white">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/5" />
        <div className="absolute -left-16 bottom-0 h-64 w-64 rounded-full bg-white/5" />
        <div className="relative max-w-6xl mx-auto px-6 py-20 lg:py-28">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
            <div className="flex-1 text-center lg:text-left">
              <span className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-white/90">
                {t('public.landing.badge')}
              </span>
              <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight mt-6 tracking-tight">
                {t('public.landing.heroTitle')}
              </h1>
              <p className="mt-5 text-light/80 max-w-xl mx-auto lg:mx-0 text-lg leading-relaxed">
                {t('public.landing.heroBody')}
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center lg:justify-start gap-4">
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 bg-coral hover:bg-coral/90 text-white px-6 py-3 rounded-xl font-semibold transition-colors shadow-lg min-h-[44px]"
                >
                  {t('public.landing.getStarted')} <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/about"
                  className="inline-flex items-center gap-2 bg-white/10 border border-white/30 text-white px-6 py-3 rounded-xl font-semibold hover:bg-white/20 transition-colors min-h-[44px]"
                >
                  {t('public.landing.learnMore')}
                </Link>
              </div>
            </div>

            {/* White logo panel -- BINDING dark-surface rule: navy linework
                must never sit directly on this navy hero. */}
            <div className="flex-shrink-0 flex justify-center">
              <div className="bg-white rounded-3xl p-8 w-64 sm:w-72 shadow-[0_0_60px_rgba(255,255,255,0.12)]">
                <Logo className="h-auto w-full" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How MyPillSafe Works ── */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-navy text-center mb-2">{t('public.landing.howTitle')}</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-10">
            {HOW_IT_WORKS.map(({ key, step, icon: Icon }) => (
              <div key={key} className="bg-light rounded-2xl p-6 border-t-4 border-teal-500 card-hover">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-3xl font-black text-teal-600">{step}</span>
                  <Icon className="h-6 w-6 text-navy" />
                </div>
                <h3 className="font-bold text-navy mb-2">{t(`public.landing.steps.${key}.title`)}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{t(`public.landing.steps.${key}.desc`)}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Three-Outcome Safety Design ── */}
      <section className="py-20 px-4 bg-light">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-navy text-center mb-3">{t('public.landing.outcomesTitle')}</h2>
          <p className="text-slate-600 text-center max-w-2xl mx-auto mb-10 leading-relaxed">
            {t('public.landing.outcomesIntro')}
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {OUTCOMES.map(({ key, icon: Icon, classes }) => (
              <div key={key} className={`rounded-2xl border p-6 ${classes}`}>
                <Icon className="h-7 w-7 mb-3" />
                <p className="font-bold mb-2">{t(`public.landing.outcomes.${key}.label`)}</p>
                <p className="text-sm leading-relaxed opacity-90">{t(`public.landing.outcomes.${key}.desc`)}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-sm text-slate-500 mt-8 max-w-2xl mx-auto leading-relaxed">
            {t('public.landing.outcomesNote')}
          </p>

          {/* Why verify instead of identify? */}
          <div className="max-w-3xl mx-auto mt-12 bg-navy text-white rounded-2xl p-8">
            <h3 className="text-xl font-bold mb-3">{t('public.landing.whyVerifyTitle')}</h3>
            <p className="text-white/75 leading-relaxed">
              <Trans i18nKey="public.landing.whyVerifyBody" components={{ em: <em /> }} />
            </p>
          </div>
        </div>
      </section>

      {/* ── Scientific Foundation strip ── */}
      <section className="py-20 px-4 bg-navy text-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-2">
            <Link to="/about/science" className="hover:text-light/80 transition-colors">
              {t('public.landing.scienceTitle')}
            </Link>
          </h2>
          <p className="text-light/60 text-center mb-10 max-w-2xl mx-auto text-sm">
            {t('public.landing.scienceIntro')}
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SCIENCE_STRIP.map(({ key, title }, i) => (
              <div key={key} className="bg-white/5 border-l-4 border-teal-500 rounded-r-xl p-5">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 bg-white/10 rounded-full text-xs flex items-center justify-center font-bold text-white">
                    {i + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-white text-sm mb-0.5">{title}</p>
                    <p className="text-xs text-teal-300 mb-2">{t(`public.landing.science.${key}.journal`)}</p>
                    <p className="text-xs text-white/70 leading-relaxed">{t(`public.landing.science.${key}.point`)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link
              to="/about/science"
              className="inline-flex items-center gap-2 text-sm font-semibold text-teal-300 hover:text-white transition-colors"
            >
              {t('public.landing.scienceCta')} <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Closing CTA ── */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-navy mb-4">{t('public.landing.closingTitle')}</h2>
          <p className="text-slate-600 mb-8 leading-relaxed">{t('public.landing.closingBody')}</p>
          <Link
            to="/about/vision"
            className="inline-flex items-center gap-2 bg-navy hover:bg-primary-dark text-white px-8 py-3 rounded-xl font-semibold transition-colors min-h-[44px]"
          >
            {t('public.landing.readVision')} <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
