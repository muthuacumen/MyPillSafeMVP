import { Sunrise, Sun, Sunset, Moon } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { TimeSlot } from '@/types';

/** Same hour boundaries as DashboardPage's per-dose `slotForTime`, applied to "now" instead of a stored time. */
export function getTimeSlot(date: Date = new Date()): TimeSlot {
  const h = date.getHours();
  if (h >= 5 && h < 12) return 'morning';
  if (h >= 12 && h < 17) return 'afternoon';
  if (h >= 17 && h < 20) return 'evening';
  return 'night';
}

export const TIME_SLOT_ICON: Record<TimeSlot, LucideIcon> = {
  morning: Sunrise,
  afternoon: Sun,
  evening: Sunset,
  night: Moon,
};

// Greeting copy lives in i18n (`dashboard.greetings.*`, i18n/locales/{en,fr}.json)
// -- TIME_SLOT_GREETING_KEY maps a slot to its translation key; consumers
// (TimeAwareHeader) resolve it via `t()` at render time.
export const TIME_SLOT_GREETING_KEY: Record<TimeSlot, string> = {
  morning: 'dashboard.greetings.morning',
  afternoon: 'dashboard.greetings.afternoon',
  evening: 'dashboard.greetings.evening',
  night: 'dashboard.greetings.night',
};

/** Hero gradient per time of day — soft sunrise, bright calm teal, warm amber
 * sunset, deep calm navy night. Phase 6 palette sweep: afternoon was
 * `from-sky-500 via-blue-600 to-blue-700` and night was
 * `from-indigo-900 via-slate-900 to-slate-950` -- both off the Phase 5
 * navy/teal system (this is the "bright-blue gradient" Muthu flagged on the
 * dashboard greeting header). Moved onto the brand teal/navy tokens. */
export const TIME_SLOT_HERO_GRADIENT: Record<TimeSlot, string> = {
  morning: 'from-amber-400 via-amber-500 to-orange-500',
  afternoon: 'from-teal-400 via-teal-500 to-teal-600',
  evening: 'from-orange-500 via-rose-500 to-rose-600',
  night: 'from-primary-dark via-navy to-slate-950',
};

/** Subtle page wash behind the dashboard, matching the tailwind.config.ts time-of-day tokens. */
export const TIME_SLOT_PAGE_WASH: Record<TimeSlot, string> = {
  morning: 'bg-morning/40',
  afternoon: 'bg-afternoon/40',
  evening: 'bg-evening/60',
  night: 'bg-night/60',
};
