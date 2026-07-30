import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AboutNav from '@/components/AboutNav';

// Content pack §6 -- names/roles transcribed verbatim; task bullets are
// Phase 6 additions (Muthu's verification item 3), written to be at parity
// with PathoIntern's team page (role + concrete responsibility list). Task
// language only -- no fabricated metrics, credentials, or awards -- each
// bullet describes a real surface this app actually has.
//
// PEOPLE'S NAMES AND INITIALS ARE NOT TRANSLATED and therefore stay here in
// code. Roles and responsibility bullets are language, and live in
// `public.team.members.*` in both locale files.
const TEAM = [
  { key: 'mj', initials: 'MJ', name: 'Muthuraj Jayakumar', avatarBg: 'bg-navy' },
  { key: 'sr', initials: 'SR', name: 'Sumanth Reddy', avatarBg: 'bg-teal-600' },
  { key: 'lr', initials: 'LR', name: 'Lohith Reddy', avatarBg: 'bg-burnt' },
  { key: 'ao', initials: 'AO', name: 'Ali Ozdemir', avatarBg: 'bg-coral' },
  { key: 'am', initials: 'AM', name: 'Abdullah Mohammed', avatarBg: 'bg-navy' },
];

const FOCUS_KEYS = ['focus1', 'focus2', 'focus3', 'focus4'] as const;

export default function TeamPage() {
  const { t } = useTranslation();

  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">{t('common.home')}</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">{t('common.about')}</Link>
            <span>/</span>
            <span className="text-white/80">{t('public.team.breadcrumb')}</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">{t('public.team.eyebrow')}</p>
          <h1 className="text-4xl font-bold">{t('public.team.title')}</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">{t('public.team.subtitle')}</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto py-12 px-4 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {TEAM.map(({ key, initials, name, avatarBg }) => (
            <div key={key} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden card-hover">
              <div className="p-6 border-b border-slate-100">
                <div className="flex items-center gap-4">
                  <div className={`${avatarBg} text-white w-14 h-14 rounded-2xl flex items-center justify-center font-black text-lg flex-shrink-0`}>
                    {initials}
                  </div>
                  <div>
                    <h2 className="font-bold text-navy leading-tight">{name}</h2>
                    <p className="text-slate-500 text-sm">{t(`public.team.members.${key}.role`)}</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-navy mb-3">
                  {t('public.team.responsibilities')}
                </h3>
                <ul className="space-y-1.5">
                  {FOCUS_KEYS.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                      {t(`public.team.members.${key}.${f}`)}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-slate-500 max-w-2xl mx-auto">{t('public.team.footerNote')}</p>

        <AboutNav current="team" />
      </div>
    </div>
  );
}
