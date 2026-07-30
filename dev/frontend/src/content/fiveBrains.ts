import { ScanLine, Eye, Scale, BookOpen, Cloud } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

/**
 * Content pack §2, "The Five Brains" -- transcribed verbatim. Layout and
 * styling are ours; the words are not.
 *
 * Lifted out of `pages/public/AboutPage.tsx` (FixbyOPUS3 Task A6) so the
 * per-brain detail pages can reuse the same icon, title and one-line role
 * as the About card that links to them, instead of a second copy that
 * silently drifts. `href` is set only for brains that HAVE a detail page --
 * all five now do: Prescription Reader shipped first as the template, and
 * Pill Vision, Deterministic Matcher, Monograph Retrieval and Answer Voice
 * followed, so every About card links through.
 *
 * Detail pages live OFF the About chain, at `/about/brains/<slug>`. They
 * are deliberately NOT in `ABOUT_PAGES` (components/AboutNav.tsx): that
 * array is the single source of truth for the linear About narrative and is
 * also consumed by Navbar and AppFooter, so five more entries would turn a
 * 5-step story into a 10-step one and bloat the site nav.
 *
 * The copy itself moved to `public.fiveBrains.*` in the locale files when
 * the public chain was translated. What stays here is what is NOT language:
 * the icon, the route, and the stable key that ties the two together.
 */
export interface BrainMeta {
  /** Stable key into `public.fiveBrains.<key>.{title,desc}` in both locales. */
  key: string;
  icon: LucideIcon;
  href?: string;
}

export const FIVE_BRAINS: BrainMeta[] = [
  { key: 'ocr', icon: ScanLine, href: '/about/brains/prescription-reader' },
  { key: 'vision', icon: Eye, href: '/about/brains/pill-vision' },
  { key: 'matcher', icon: Scale, href: '/about/brains/deterministic-matcher' },
  { key: 'retrieval', icon: BookOpen, href: '/about/brains/monograph-retrieval' },
  { key: 'voice', icon: Cloud, href: '/about/brains/answer-voice' },
];
