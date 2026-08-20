import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ShieldAlert } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { Logo } from '@/components/ui/Logo';
import { ABOUT_PAGES } from '@/components/AboutNav';
import { TEAM } from '@/data/team';

export function AppFooter() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const { t } = useTranslation();

  return (
    <footer className="border-t border-white/10 bg-navy text-white">
      <div className="max-w-6xl mx-auto px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-10">
          <div>
            <Link to="/" className="inline-flex items-center focus-visible:ring">
              <Logo onDark className="h-8" />
            </Link>
            <p className="text-sm text-white/60 mt-3 max-w-xs leading-relaxed">
              {t('footer.tagline')}
            </p>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">{t('footer.explore')}</p>
            <ul className="space-y-2.5 text-sm">
              <li><Link to="/" className="text-white/70 hover:text-white transition-colors">{t('footer.home')}</Link></li>
              <li><Link to="/contact" className="text-white/70 hover:text-white transition-colors">{t('footer.contact')}</Link></li>
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">{t('footer.aboutHeading')}</p>
            <ul className="space-y-2.5 text-sm">
              {ABOUT_PAGES.map((p) => (
                <li key={p.id}>
                  <Link to={p.href} className="text-white/70 hover:text-white transition-colors">
                    {t(p.labelKey)}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-semibold text-white/40 uppercase tracking-wider mb-3">{t('footer.account')}</p>
            <ul className="space-y-2.5 text-sm">
              {isAuthenticated ? (
                <li><Link to="/dashboard" className="text-white/70 hover:text-white transition-colors">{t('footer.dashboard')}</Link></li>
              ) : (
                <>
                  <li><Link to="/login" className="text-white/70 hover:text-white transition-colors">{t('footer.signIn')}</Link></li>
                  <li><Link to="/register" className="text-white/70 hover:text-white transition-colors">{t('footer.getStarted')}</Link></li>
                </>
              )}
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-white/10 flex flex-col sm:flex-row sm:items-center gap-3">
          <div className="flex items-start gap-2 text-xs text-white/60 leading-relaxed">
            <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
            <p>{t('footer.disclaimer')}</p>
          </div>
          {/* `footer.credits` is the translated prefix ONLY ("MyPillSafe ·
              2026 ·"); the names come from @/data/team because names are not
              language. Wrapping (not shrink-0) on the container: five linked
              names do not fit one phone-width line, and clipping the last two
              people is worse than a second line. */}
          <p className="text-xs text-white/40 sm:ml-auto sm:text-right">
            {t('footer.credits')}{' '}
            {TEAM.map(({ key, name, linkedin }, i) => (
              <span key={key} className="whitespace-nowrap">
                {i > 0 && <span aria-hidden="true">, </span>}
                <a
                  href={linkedin}
                  target="_blank"
                  rel="noopener noreferrer"
                  aria-label={t('public.team.linkedinAria', { name })}
                  className="text-white/60 hover:text-white underline decoration-white/20 underline-offset-2 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-teal-400 rounded"
                >
                  {name}
                </a>
              </span>
            ))}
          </p>
        </div>
      </div>
    </footer>
  );
}
