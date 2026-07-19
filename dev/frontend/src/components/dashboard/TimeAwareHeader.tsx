import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ScanLine, ArrowRight } from 'lucide-react';
import { getTimeSlot, TIME_SLOT_ICON, TIME_SLOT_GREETING, TIME_SLOT_HERO_GRADIENT } from '@/lib/timeOfDay';

interface TimeAwareHeaderProps {
  firstName: string;
  tagline: string;
  analyzeLabel: string;
}

/**
 * Owns the only 1-second clock tick in the dashboard, isolated in its own
 * subtree so schedule/stat cards below don't re-render every second.
 */
export function TimeAwareHeader({ firstName, tagline, analyzeLabel }: TimeAwareHeaderProps) {
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  const slot = getTimeSlot(now);
  const Icon = TIME_SLOT_ICON[slot];
  const greeting = TIME_SLOT_GREETING[slot];
  const timeLabel = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  const dateLabel = now.toLocaleDateString([], { weekday: 'long', month: 'long', day: 'numeric' });
  const name = firstName.charAt(0).toUpperCase() + firstName.slice(1);

  return (
    <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-r ${TIME_SLOT_HERO_GRADIENT[slot]} p-6`}>
      <div className="absolute -right-8 -top-8 h-32 w-32 rounded-full bg-white/10" />
      <div className="absolute -right-4 bottom-0 h-24 w-24 rounded-full bg-white/5" />
      <div className="relative z-10 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-white/80 text-sm font-medium">
            <Icon className="h-4 w-4" />
            <span>{greeting}</span>
            <span aria-hidden="true">·</span>
            <time dateTime={now.toISOString()} className="tabular-nums">{timeLabel}</time>
          </div>
          <h1 className="text-2xl font-extrabold text-white mt-0.5">{name}!</h1>
          <p className="text-white/70 text-sm mt-1.5 max-w-md">{tagline}</p>
          <p className="text-white/50 text-xs mt-1">{dateLabel}</p>
        </div>
        <Link
          to="/dashboard/analyze"
          className="inline-flex items-center gap-2 bg-white text-slate-900 px-5 py-2.5 rounded-xl text-sm font-semibold hover:bg-slate-50 transition-colors shrink-0 shadow-lg min-h-[44px]"
        >
          <ScanLine className="h-4 w-4" />
          {analyzeLabel}
          <ArrowRight className="h-4 w-4" />
        </Link>
      </div>
    </div>
  );
}
