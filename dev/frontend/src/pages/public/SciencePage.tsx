import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { FlaskConical, ShieldCheck, MessageSquareWarning, ShieldOff, ExternalLink } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §5 -- transcribed verbatim. Layout/styling is ours; words are
// not.
//
// Phase 6 (Muthu's verification item 1): every citation whose DOI/venue was
// marked VERIFIED in the Phase 5 Grounding block of INTEGRATION_PLAN.md gets
// an outbound link (new tab, rel="noopener noreferrer"). MedSnap ID and
// Hanley & Lippman-Hand are deliberately left unlinked here -- they were not
// part of the closed VERIFIED set this phase's spec named, so no URL is
// invented for them (never guess a DOI).
//
// BIBLIOGRAPHIC IDENTITY IS NOT TRANSLATED. Author names, paper titles and
// DOIs are the citation itself and stay here in code; the venue label and the
// explanatory "point" are language and live in `public.science.citations.*`.
// (Venue strings are identical in both locales except where they are prose --
// "Population evidence" -> "Données de population".) The CIHI report title is
// cited in the language it was published in, not re-titled by us.
const CITATIONS = [
  {
    key: 'nlm',
    title: 'Yaniv et al. — The NLM Pill Image Recognition Challenge',
    url: 'https://doi.org/10.1109/AIPR.2016.8010584',
  },
  {
    key: 'mobiledeeppill',
    title: 'Zeng, Cao & Zhang — MobileDeepPill',
    url: 'https://doi.org/10.1145/3081333.3081336',
  },
  {
    key: 'epillid',
    title: 'Usuyama et al. — ePillID',
    url: 'https://arxiv.org/abs/2005.14288',
  },
  {
    key: 'fewshot',
    title: 'Ling et al. — Few-Shot Pill Recognition',
    url: 'https://doi.org/10.1109/CVPR42600.2020.00981',
  },
  {
    key: 'gopill',
    title: 'GO-PILL',
    url: 'https://www.mdpi.com/2227-7390/14/2/356',
  },
  {
    key: 'medic',
    title: 'MEDIC — Large language models for preventing medication direction errors in online pharmacies',
    url: 'https://www.nature.com/articles/s41591-024-02933-8',
  },
  {
    key: 'medsnap',
    title: 'MedSnap ID',
  },
  {
    key: 'hanley',
    title: 'Hanley & Lippman-Hand',
  },
  {
    key: 'cihi',
    title: 'CIHI — Drug Use Among Seniors in Canada',
    url: 'https://www.cihi.ca/en/drug-use-among-seniors-in-canada',
  },
];

const PRINCIPLES = [
  { key: 'verify', icon: ShieldCheck },
  { key: 'separation', icon: MessageSquareWarning },
  { key: 'abstention', icon: ShieldOff },
];

export default function SciencePage() {
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
            <span className="text-white/80">{t('public.science.breadcrumb')}</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">{t('public.science.eyebrow')}</p>
          <h1 className="text-4xl font-bold">{t('public.science.title')}</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">{t('public.science.subtitle')}</p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Section A -- published evidence */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">{t('public.science.publishedTitle')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CITATIONS.map(({ key, title, url }, i) => (
              <div key={key} className="bg-light border-l-4 border-teal-500 rounded-r-xl p-5">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 bg-navy/10 rounded-full text-xs flex items-center justify-center font-bold text-navy">
                    {i + 1}
                  </span>
                  <div>
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-navy text-sm mb-0.5 inline-flex items-center gap-1 hover:text-teal-700 hover:underline"
                      >
                        {title}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <p className="font-semibold text-navy text-sm mb-0.5">{title}</p>
                    )}
                    <p className="text-xs text-teal-700 mb-2 mt-0.5">{t(`public.science.citations.${key}.journal`)}</p>
                    <p className="text-xs text-slate-600 leading-relaxed">{t(`public.science.citations.${key}.point`)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section B -- our own research (in preparation) */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center shrink-0">
              <FlaskConical className="w-5 h-5 text-warning-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">{t('public.science.ourResearchTitle')}</h2>
            <span className="inline-flex items-center bg-warning-bg text-warning-text border border-warning-border text-[11px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full">
              {t('public.science.inPreparation')}
            </span>
          </div>

          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">
            {t('public.science.workingTitleLabel')}
          </p>
          {/* The paper's working title is a title, not prose -- it stays in
              English in both locales, wrapped in the target language's quotes. */}
          <p className="text-lg font-semibold text-navy italic mb-5 leading-snug">
            {t('public.science.workingTitle')}
          </p>

          <p className="text-slate-700 leading-relaxed mb-5">{t('public.science.researchBody')}</p>

          <div className="bg-warning-bg border border-warning-border rounded-xl p-5">
            <p className="text-sm text-warning-text leading-relaxed">
              <strong>{t('public.science.statusLabel')}</strong> {t('public.science.statusBody')}
            </p>
          </div>
        </div>

        {/* Section C -- design principles */}
        <div className="bg-navy text-white rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-5">{t('public.science.principlesTitle')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PRINCIPLES.map(({ key, icon: Icon }) => (
              <div key={key} className="bg-white/5 rounded-xl p-5">
                <Icon className="h-5 w-5 text-teal-300 mb-3" />
                <h3 className="font-bold text-white text-sm mb-2">{t(`public.science.principles.${key}.title`)}</h3>
                <p className="text-xs text-white/70 leading-relaxed">{t(`public.science.principles.${key}.desc`)}</p>
              </div>
            ))}
          </div>
        </div>

        <AboutNav current="science" />
      </div>
    </div>
  );
}
