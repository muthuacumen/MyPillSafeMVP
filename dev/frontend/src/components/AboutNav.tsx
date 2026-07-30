import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ArrowRight } from 'lucide-react';

// ─────────────────────────────────────────────────────────────────────────
// Single source of truth for the about-page chain order (content pack §7):
// Home -> About -> Vision & Mission -> Problem Statement -> Scientific
// Foundation -> Team -> Get Started (/register). Contact stays outside the
// chain, linked from the footer only. `labelKey` resolves against
// `about.nav.*` in both locales (i18n/locales/{en,fr}.json) -- consumers
// (this file, Navbar, AppFooter) translate it at render time via `t()`.
// ─────────────────────────────────────────────────────────────────────────
export interface AboutPageMeta {
  id: string;
  href: string;
  labelKey: string;
}

export const ABOUT_PAGES: AboutPageMeta[] = [
  { id: 'about', href: '/about', labelKey: 'about.nav.about' },
  { id: 'vision', href: '/about/vision', labelKey: 'about.nav.vision' },
  { id: 'problem', href: '/about/problem', labelKey: 'about.nav.problem' },
  { id: 'science', href: '/about/science', labelKey: 'about.nav.science' },
  { id: 'team', href: '/about/team', labelKey: 'about.nav.team' },
];

interface AboutNavProps {
  /** The `id` of the current about page, e.g. "vision", "team". */
  current: string;
}

export default function AboutNav({ current }: AboutNavProps) {
  const { t } = useTranslation();
  const idx = ABOUT_PAGES.findIndex((p) => p.id === current);

  const prev =
    idx > 0
      ? { href: ABOUT_PAGES[idx - 1].href, label: t(ABOUT_PAGES[idx - 1].labelKey) }
      : { href: '/', label: t('about.nav.backToHome') };

  const isLast = idx === ABOUT_PAGES.length - 1;
  const next = isLast
    ? { href: '/register', label: t('about.nav.getStarted') }
    : { href: ABOUT_PAGES[idx + 1].href, label: t(ABOUT_PAGES[idx + 1].labelKey) };

  return (
    <div className="flex flex-col sm:flex-row gap-3">
      <Link
        to={prev.href}
        className="flex-1 border border-navy text-navy text-center py-3 rounded-xl font-semibold hover:bg-navy hover:text-white transition-colors inline-flex items-center justify-center gap-2 min-h-[44px]"
      >
        <ArrowLeft className="h-4 w-4 flex-shrink-0" />
        {prev.label}
      </Link>
      <Link
        to={next.href}
        className={`flex-1 text-center py-3 rounded-xl font-semibold transition-colors inline-flex items-center justify-center gap-2 min-h-[44px] ${
          isLast ? 'bg-coral text-white hover:bg-coral/90' : 'bg-navy text-white hover:bg-primary-dark'
        }`}
      >
        {next.label}
        <ArrowRight className="h-4 w-4 flex-shrink-0" />
      </Link>
    </div>
  );
}
