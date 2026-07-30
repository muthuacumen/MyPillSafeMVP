import { useEffect, useState } from 'react';
import { Users, Activity, ShieldCheck, BarChart3 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi, type PlatformStats, type AnalysisSummary } from '@/api/admin';

function StatTile({ icon: Icon, label, value, iconBg }: { icon: React.ElementType; label: string; value: number; iconBg: string }) {
  return (
    <div className="stat-card">
      <div className={`h-11 w-11 rounded-xl flex items-center justify-center shrink-0 ${iconBg}`}>
        <Icon className="h-5 w-5" strokeWidth={1.8} />
      </div>
      <div>
        <p className="text-xs text-slate-500 font-medium">{label}</p>
        <p className="text-2xl font-bold text-slate-900 mt-0.5">{value}</p>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const { t } = useTranslation();
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [analyses, setAnalyses] = useState<AnalysisSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      adminApi.getStats(),
      adminApi.listAnalyses(0, 10),
    ]).then(([s, a]) => {
      setStats(s.data);
      setAnalyses(a.data);
    }).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 rounded-full border-2 border-teal-600 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter max-w-5xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t('admin.dashboard')}</h1>
        <p className="text-sm text-slate-500 mt-1">{t('admin.stats')}</p>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile icon={Users} label={t('admin.totalUsers')} value={stats.total_users} iconBg="bg-teal-50 text-teal-600" />
          <StatTile icon={Activity} label={t('admin.activeUsers')} value={stats.active_users} iconBg="bg-blue-50 text-blue-600" />
          <StatTile icon={BarChart3} label={t('admin.totalAnalyses')} value={stats.total_analyses} iconBg="bg-purple-50 text-purple-600" />
          <StatTile icon={ShieldCheck} label={t('admin.admins')} value={stats.admin_count} iconBg="bg-amber-50 text-amber-600" />
        </div>
      )}

      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-100">
          <h2 className="font-semibold text-slate-900 text-sm">{t('admin.recentAnalyses')}</h2>
        </div>
        {analyses.length === 0 ? (
          <p className="px-5 py-8 text-center text-sm text-slate-400">{t('common.noData')}</p>
        ) : (
          <div className="divide-y divide-slate-50">
            {analyses.map((a) => (
              <div key={a.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">
                    {a.image_filename ?? 'No image'}
                  </p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    User {a.user_id.slice(0, 8)}… · {new Date(a.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span className={`badge ${a.status === 'completed' ? 'bg-teal-50 text-teal-700 border border-teal-200' : 'bg-slate-100 text-slate-500'}`}>
                    {a.status}
                  </span>
                  {/* "ML" is a technical abbreviation on an admin-only surface
                      and reads the same in both locales, so it is not keyed. */}
                  {a.ml_pipeline_enabled && (
                    <span className="badge bg-purple-50 text-purple-700 border border-purple-200">ML</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
