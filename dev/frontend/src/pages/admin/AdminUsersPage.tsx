import { useEffect, useMemo, useState } from 'react';
import { UserCheck, UserX, Trash2, Shield, Clock } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { adminApi, type AdminUser } from '@/api/admin';
import { useAuthStore } from '@/store/authStore';

export default function AdminUsersPage() {
  const { t } = useTranslation();
  const me = useAuthStore((s) => s.user);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    adminApi.listUsers().then((r) => setUsers(r.data)).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const withAction = async (id: string, fn: () => Promise<unknown>) => {
    setActionLoading(id);
    try { await fn(); load(); } finally { setActionLoading(null); }
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

      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50 text-left">
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('admin.email')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('admin.patientName')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.role')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.status')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.joinDate')}</th>
                <th className="px-4 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">{t('common.actions')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-50">
              {users.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">{t('common.noData')}</td>
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

                          {/* Delete */}
                          <button
                            disabled={isSelf || busy}
                            title={t('common.delete')}
                            onClick={() => {
                              if (window.confirm(t('admin.confirmDelete'))) {
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
      </div>
    </div>
  );
}
