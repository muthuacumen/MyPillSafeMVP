import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, Eye, Compass, Languages, HeartHandshake } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §3 -- transcribed verbatim. Layout/styling is ours; words are
// not. The copy lives in `public.vision.*` in both locale files; what stays
// here is the icon and the border/text colour pairing per value.

const VALUES = [
  { key: 'safety', icon: ShieldCheck, color: 'border-warning-border text-warning-text' },
  { key: 'evidence', icon: Eye, color: 'border-teal-300 text-teal-700' },
  { key: 'language', icon: Languages, color: 'border-navy/30 text-navy' },
  { key: 'honesty', icon: HeartHandshake, color: 'border-coral/30 text-coral' },
];

export default function VisionPage() {
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
            <span className="text-white/80">{t('public.vision.breadcrumb')}</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">{t('public.vision.eyebrow')}</p>
          <h1 className="text-4xl font-bold">{t('public.vision.title')}</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Mission (hero statement) */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-navy/10 flex items-center justify-center">
              <Compass className="w-5 h-5 text-navy" />
            </div>
            <h2 className="text-2xl font-bold text-navy">{t('public.vision.missionTitle')}</h2>
          </div>
          <blockquote className="text-xl sm:text-2xl text-navy font-semibold italic border-l-4 border-coral pl-5 leading-relaxed">
            {t('public.vision.mission')}
          </blockquote>
        </div>

        {/* Vision */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
              <Eye className="w-5 h-5 text-teal-600" />
            </div>
            <h2 className="text-2xl font-bold text-navy">{t('public.vision.visionTitle')}</h2>
          </div>
          <p className="text-slate-700 leading-relaxed text-lg">{t('public.vision.vision')}</p>
        </div>

        {/* Values */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">{t('public.vision.valuesTitle')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {VALUES.map(({ key, icon: Icon, color }) => (
              <div key={key} className={`bg-light rounded-xl p-5 border-l-4 ${color.split(' ')[0]}`}>
                <Icon className={`h-5 w-5 mb-2 ${color.split(' ')[1]}`} />
                <h3 className="font-bold text-navy text-sm mb-1.5">{t(`public.vision.values.${key}.title`)}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{t(`public.vision.values.${key}.desc`)}</p>
              </div>
            ))}
          </div>
        </div>

        <AboutNav current="vision" />
      </div>
    </div>
  );
}
