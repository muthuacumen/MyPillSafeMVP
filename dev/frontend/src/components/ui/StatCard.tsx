import { memo, type ReactNode } from 'react';
import { TrendingUp } from 'lucide-react';

interface StatCardProps {
  label: string;
  value: string;
  sub?: string;
  icon: ReactNode;
  iconBg?: string;
  trend?: string;
}

export const StatCard = memo(function StatCard({
  label,
  value,
  sub,
  icon,
  iconBg = 'bg-teal-50 text-teal-600',
  trend,
}: StatCardProps) {
  return (
    <div className="stat-card">
      <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>{icon}</div>
      <div className="flex-1 min-w-0">
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
        {sub && <p className="text-xs text-slate-400 mt-0.5">{sub}</p>}
      </div>
      {trend && (
        <div className="flex items-center gap-1 text-teal-600 text-xs font-medium">
          <TrendingUp className="h-3.5 w-3.5" />
          {trend}
        </div>
      )}
    </div>
  );
});
