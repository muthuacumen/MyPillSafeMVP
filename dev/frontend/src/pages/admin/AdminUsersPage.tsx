import { useEffect, useMemo, useState } from 'react';
import { UserCheck, UserX, Trash2, Shield, Clock, LogOut, Users, Activity, BarChart3, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi, type AdminUser, type PlatformStats } from '@/api/admin';
import { useAuthStore } from '@/store/authStore';
import { Alert } from '@/components/ui/Alert';
import { extractApiErrorMessage } from '@/lib/apiError';

const PAGE_SIZE = 20;

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

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const me = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState('');
  const [actionNote, setActionNote] = useState('');
  const [skip, setSkip] = useState(0);
  // Returned page shorter than PAGE_SIZE (or empty) means there's no next
  // page -- the /admin/users list endpoint doesn't return a total count, so
  // this is the only signal available to disable "Next" honestly.
  const [hasNextPage, setHasNextPage] = useState(false);

  const load = (nextSkip = skip) => {
    setLoading(true);
    adminApi.listUsers(nextSkip, PAGE_SIZE)
      .then((r) => {
        setUsers(r.data);
        setHasNextPage(r.data.length === PAGE_SIZE);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(skip); }, [skip]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { adminApi.getStats().then((r) => setStats(r.data)); }, []);

  const withAction = async (id: string, fn: () => Promise<unknown>) => {
    setActionLoading(id);
    setActionError('');
    try {
      await fn();
      load();
    } catch (err) {
      setActionError(extractApiErrorMessage(err, t('admin.actionFailed')));
    } finally {
      setActionLoading(null);
    }
  };

  const handleTerminateSessions = async (id: string) => {
    if (!window.confirm(t('admin.confirmTerminateSessions'))) return;
    setActionLoading(id);
    setActionError('');
    setActionNote('');
    try {
      const { data } = await adminApi.terminateSessions(id);
      setActionNote(t('admin.sessionsTerminated', { version: data.token_version }));
    } catch (err) {
      setActionError(extractApiErrorMessage(err, t('admin.actionFailed')));
    } finally {
      setActionLoading(null);
    }
  };

  // Pending signups float to the top: this table is now an approval queue as
  // well as a directory, and a new account is the only row here that someone
  // is actively waiting on. Sorted, not filtered into a separate view — the
  // existing activate endpoint IS the approve action, so there is one list
  // and one control, just ordered by who needs attention.
  const sorted = useMemo(
    () => [...users].sort((a, b) => Number(a.is_active) - Number(b.is_active)),
    [users],
  );
  const pendingCount = useMemo(() => users.filter((u) => !u.is_active).length, [users]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="h-8 w-8 rounded-full border-2 border-teal-600 border-t-transparent animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 page-enter max-w-6xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t('admin.users')}</h1>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          <p className="text-sm text-slate-500">{users.length} {t('admin.allUsers').toLowerCase()}</p>
          {pendingCount > 0 && (
            <span className="badge bg-amber-50 text-amber-700 border border-amber-200 inline-flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {t('admin.pendingSummary', { count: pendingCount })}
            </span>
          )}
        </div>
      </div>

      {stats && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <StatTile icon={Users} label={t('admin.totalUsers')} value={stats.total_users} iconBg="bg-teal-50 text-teal-600" />
          <StatTile icon={Activity} label={t('admin.activeUsers')} value={stats.active_users} iconBg="bg-blue-50 text-blue-600" />
          <StatTile icon={BarChart3} label={t('admin.totalAnalyses')} value={stats.total_analyses} iconBg="bg-purple-50 text-purple-600" />
          <StatTile icon={ShieldCheck} label={t('admin.admins')} value={stats.admin_count} iconBg="bg-amber-50 text-amber-600" />
        </div>
      )}

      {actionError && <Alert variant="error" message={actionError} />}
      {actionNote && <Alert variant="success" message={actionNote} />}

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('admin.email')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('admin.patientName')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.role')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.status')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('admin.verifiedColumn')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.joinDate')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-slate-400">{t('common.noData')}</td>
                </tr>
              ) : (
                sorted.map((u) => {
                  const isSelf = u.id === me?.id;
                  const busy = actionLoading === u.id;
                  const isPending = !u.is_active;
                  const patientName = u.patient
                    ? `${u.patient.first_name} ${u.patient.last_name}`
                    : t('admin.noPatient');

                  return (
                    <tr
                      key={u.id}
                      className={`transition-colors ${isPending ? 'bg-amber-50/40 hover:bg-amber-50/70' : 'hover:bg-slate-50/50'}`}
                    >
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-slate-900">{u.email}</p>
                          {isSelf && <span className="text-xs text-teal-600 font-medium">(you)</span>}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-600">{patientName}</td>
                      <td className="px-4 py-3">
                        <span className={`badge ${u.role === 'ADMIN' ? 'bg-amber-50 text-amber-700 border border-amber-200' : 'bg-slate-100 text-slate-600'}`}>
                          {u.role}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {/* "Pending approval", not "Inactive": inactive reads
                            as an account someone switched OFF. Every new
                            signup lands here, and amber-as-queued is a very
                            different instruction to an admin than red-as-
                            disabled. */}
                        <span className={`badge inline-flex items-center gap-1 ${u.is_active ? 'bg-teal-50 text-teal-700 border border-teal-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                          {isPending && <Clock className="h-3 w-3" />}
                          {u.is_active ? t('common.active') : t('admin.pendingApproval')}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <span className={`badge ${u.is_verified ? 'bg-teal-50 text-teal-700 border border-teal-200' : 'bg-slate-100 text-slate-500'}`}>
                          {u.is_verified ? t('admin.verified') : t('admin.unverified')}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-500 text-xs">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1">
                          {/* Toggle active */}
                          {u.is_active ? (
                            <button
                              disabled={isSelf || busy}
                              title={t('common.deactivate')}
                              onClick={() => withAction(u.id, () => adminApi.deactivateUser(u.id))}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-amber-600 hover:bg-amber-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                            >
                              <UserX className="h-4 w-4" />
                            </button>
                          ) : (
                            // Same endpoint as before — for a pending signup
                            // "activate" IS "approve", so this relabels
                            // rather than adding a second API.
                            <button
                              disabled={busy}
                              title={t('admin.approve')}
                              aria-label={t('admin.approve')}
                              onClick={() => withAction(u.id, () => adminApi.activateUser(u.id))}
                              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold text-teal-700 bg-teal-50 border border-teal-200 hover:bg-teal-100 transition-colors disabled:opacity-30"
                            >
                              <UserCheck className="h-4 w-4" />
                              {t('admin.approve')}
                            </button>
                          )}

                          {/* Toggle role */}
                          <button
                            disabled={isSelf || busy}
                            title={t('admin.changeRole')}
                            onClick={() => {
                              const newRole = u.role === 'ADMIN' ? 'PATIENT' : 'ADMIN';
                              if (window.confirm(`Change role to ${newRole}?`)) {
                                withAction(u.id, () => adminApi.updateRole(u.id, newRole));
                              }
                            }}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-purple-600 hover:bg-purple-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <Shield className="h-4 w-4" />
                          </button>

                          {/* Terminate sessions -- kills every token this
                              user currently holds (tv bump) without
                              deactivating the account, e.g. after a lost
                              device. Separate from Deactivate, which also
                              blocks new logins. */}
                          <button
                            disabled={busy}
                            title={t('admin.terminateSessions')}
                            aria-label={t('admin.terminateSessions')}
                            onClick={() => handleTerminateSessions(u.id)}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-blue-600 hover:bg-blue-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <LogOut className="h-4 w-4" />
                          </button>

                          {/* Delete -- double confirm: this is the one
                              irreversible action in the table (permanently
                              removes the user and their data), so a single
                              click-through confirm isn't enough friction. */}
                          <button
                            disabled={isSelf || busy}
                            title={t('common.delete')}
                            onClick={() => {
                              if (window.confirm(t('admin.confirmDelete')) && window.confirm(t('admin.confirmDeleteFinal'))) {
                                withAction(u.id, () => adminApi.deleteUser(u.id));
                              }
                            }}
                            className="p-1.5 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-100">
          <p className="text-xs text-slate-500">
            {users.length > 0
              ? t('admin.paginationRange', { start: skip + 1, end: skip + users.length })
              : t('common.noData')}
          </p>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={skip === 0}
              onClick={() => setSkip((s) => Math.max(0, s - PAGE_SIZE))}
              className="btn-secondary !px-3 !py-1.5 !text-xs"
            >
              {t('common.previous')}
            </button>
            <button
              type="button"
              disabled={!hasNextPage}
              onClick={() => setSkip((s) => s + PAGE_SIZE)}
              className="btn-secondary !px-3 !py-1.5 !text-xs"
            >
              {t('common.next')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
