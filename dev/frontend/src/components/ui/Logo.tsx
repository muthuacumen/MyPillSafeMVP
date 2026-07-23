/** MyPillSafe brand mark (Phase 5, §B). Wraps the SA-prepared PNGs in
 * `public/` -- `logo.png` (653x521, mark + wordmark) is the default;
 * `logo-mark.png` (400x400, mark only) is for compact/icon-only spots.
 *
 * BINDING dark-surface rule: both PNGs' linework is navy, so they must
 * never sit directly on a navy/dark surface -- `onDark` wraps the image in
 * a white rounded chip (the PathoIntern hero pattern). Never reference
 * `MyPillSafe_Logo.png` (the untouched original source asset) here.
 */
interface LogoProps {
  /** 'full' = logo.png (mark + wordmark), 'mark' = logo-mark.png only. */
  variant?: 'full' | 'mark';
  /** True when rendered on a navy/dark background -- wraps in a white chip. */
  onDark?: boolean;
  /** Height utility applied to the <img> itself, e.g. 'h-8'. */
  className?: string;
  /** Extra classes for the white chip wrapper (only used when onDark). */
  chipClassName?: string;
}

export function Logo({ variant = 'full', onDark = false, className = 'h-8', chipClassName = '' }: LogoProps) {
  const src = variant === 'mark' ? '/logo-mark.png' : '/logo.png';
  const img = <img src={src} alt="MyPillSafe" className={`${className} w-auto`} />;

  if (!onDark) return img;

  return (
    <span className={`inline-flex items-center bg-white rounded-lg px-3 py-1.5 shadow-sm ${chipClassName}`}>
      {img}
    </span>
  );
}
