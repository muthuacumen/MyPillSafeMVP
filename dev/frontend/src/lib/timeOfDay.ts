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

export const TIME_SLOT_GREETING: Record<TimeSlot, string> = {
  morning: 'Good morning',
  afternoon: 'Good afternoon',
  evening: 'Good evening',
  night: 'Good night',
};

/** Hero gradient per time of day — soft sunrise, bright calm blue, warm amber sunset, deep calm night. */
export const TIME_SLOT_HERO_GRADIENT: Record<TimeSlot, string> = {
  morning: 'from-amber-400 via-amber-500 to-orange-500',
  afternoon: 'from-sky-500 via-blue-600 to-blue-700',
  evening: 'from-orange-500 via-rose-500 to-rose-600',
  night: 'from-indigo-900 via-slate-900 to-slate-950',
};

/** Subtle page wash behind the dashboard, matching the tailwind.config.ts time-of-day tokens. */
export const TIME_SLOT_PAGE_WASH: Record<TimeSlot, string> = {
  morning: 'bg-morning/40',
  afternoon: 'bg-afternoon/40',
  evening: 'bg-evening/60',
  night: 'bg-night/60',
};
