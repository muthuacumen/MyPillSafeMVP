import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { Ruler, ClipboardCheck, BarChart3, TestTube2, ArrowRight, Maximize2, X } from 'lucide-react';
import AboutNav from '@/components/AboutNav';
import { FIVE_BRAINS } from '@/content/fiveBrains';

// Rendered from public/ rather than imported: it is a 13 KB static asset with
// no build-time processing to do, and an <img src> lets the browser cache it
// independently of the JS bundle.
const DIAGRAM_SRC = '/architecture-c4-v9b.svg';

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
  const [zoomed, setZoomed] = useState(false);
  // Where focus goes when the overlay closes. Without this, dismissing the
  // lightbox drops a keyboard user back at the top of the document and they
  // have to tab all the way down to where they were.
  const openerRef = useRef<HTMLButtonElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!zoomed) return;
    closeRef.current?.focus();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setZoomed(false);
    };
    document.addEventListener('keydown', onKeyDown);
    // A 2150px-wide diagram scrolls; letting the page behind it scroll too is
    // disorienting on touch.
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.body.style.overflow = previousOverflow;
    };
  }, [zoomed]);

  const closeZoom = () => {
    setZoomed(false);
    openerRef.current?.focus();
  };

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

        {/* Architecture diagram (C4 level 2) */}
        <figure className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          <figcaption className="px-8 pt-8 pb-5">
            <h2 className="text-2xl font-bold text-navy mb-3">{t('public.about.diagramTitle')}</h2>
            <p className="text-slate-700 leading-relaxed">{t('public.about.diagramCaption')}</p>
          </figcaption>
          {/* The whole plate is the zoom control. A C4 diagram at 2150px wide
              is unreadable on a phone, so "click to enlarge" is not a nicety
              here — it is the only way the content is legible at all. */}
          <button
            ref={openerRef}
            type="button"
            onClick={() => setZoomed(true)}
            aria-label={t('public.about.diagramZoomLabel')}
            className="group relative block w-full bg-light border-t border-slate-100 p-4 sm:p-6 cursor-zoom-in focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-teal-500"
          >
            <img
              src={DIAGRAM_SRC}
              alt={t('public.about.diagramAlt')}
              loading="lazy"
              className="w-full h-auto"
            />
            <span className="absolute top-6 right-6 sm:top-8 sm:right-8 inline-flex items-center gap-1.5 rounded-lg bg-navy/85 px-2.5 py-1.5 text-xs font-medium text-white opacity-90 group-hover:opacity-100 transition-opacity">
              <Maximize2 className="h-3.5 w-3.5" />
              {t('public.about.diagramZoomHint')}
            </span>
          </button>
        </figure>

        {zoomed && (
          <div
            role="dialog"
            aria-modal="true"
            aria-label={t('public.about.diagramTitle')}
            onClick={closeZoom}
            className="fixed inset-0 z-50 bg-slate-900/90 backdrop-blur-sm overflow-auto p-4 sm:p-8"
          >
            <button
              ref={closeRef}
              type="button"
              onClick={closeZoom}
              aria-label={t('public.about.diagramCloseLabel')}
              className="fixed top-4 right-4 z-10 inline-flex items-center justify-center h-11 w-11 rounded-xl bg-white/10 text-white hover:bg-white/20 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400"
            >
              <X className="h-5 w-5" />
            </button>
            {/* Full native width with horizontal scroll rather than
                fit-to-screen: shrinking a 2150px diagram to a 390px viewport
                is exactly the illegibility the overlay exists to solve.
                stopPropagation so panning the image doesn't dismiss it. */}
            <img
              src={DIAGRAM_SRC}
              alt={t('public.about.diagramAlt')}
              onClick={(e) => e.stopPropagation()}
              className="max-w-none w-[2150px] h-auto mx-auto rounded-lg bg-white"
            />
          </div>
        )}

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
