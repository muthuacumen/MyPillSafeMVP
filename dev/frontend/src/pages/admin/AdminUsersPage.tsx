import { useEffect, useState } from 'react';
import { UserCheck, UserX, Trash2, Shield } from 'lucide-react';
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
        <p className="text-sm text-slate-500 mt-1">{users.length} {t('admin.allUsers').toLowerCase()}</p>
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
                users.map((u) => {
                  const isSelf = u.id === me?.id;
                  const busy = actionLoading === u.id;
                  const patientName = u.patient
                    ? `${u.patient.first_name} ${u.patient.last_name}`
                    : t('admin.noPatient');

                  return (
                    <tr key={u.id} className="hover:bg-slate-50/50 transition-colors">
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
                        <span className={`badge ${u.is_active ? 'bg-teal-50 text-teal-700 border border-teal-200' : 'bg-red-50 text-red-600 border border-red-200'}`}>
                          {u.is_active ? t('common.active') : t('common.inactive')}
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
                            <button
                              disabled={busy}
                              title={t('common.activate')}
                              onClick={() => withAction(u.id, () => adminApi.activateUser(u.id))}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition-colors disabled:opacity-30"
                            >
                              <UserCheck className="h-4 w-4" />
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
