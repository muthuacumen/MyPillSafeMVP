import client from './client';

export interface PatientBasicOut {
  first_name: string;
  last_name: string;
  medications_analyzed: number;
}

export interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  patient: PatientBasicOut | null;
}

export interface PlatformStats {
  total_users: number;
  active_users: number;
  total_analyses: number;
  admin_count: number;
}

export interface AnalysisSummary {
  id: string;
  user_id: string;
  status: string;
  image_filename: string | null;
  guidance: string | null;
  ml_pipeline_enabled: boolean;
  created_at: string;
}

export interface TerminateSessionsResponse {
  message: string;
  token_version: number;
}

/** `GET /admin/sidecar/status` passthrough body (Task T2 Supervisor proxy --
 * `dev/backend/app/api/v1/routes/admin_sidecar.py`). Every field beyond
 * `sidecar_running` is optional: the proxy forwards the Supervisor's JSON
 * verbatim, so a Supervisor build that hasn't shipped a given metric yet
 * (or one that omits it while the sidecar is stopped) must not break the
 * status card -- render what's present, omit the rest. */
export interface SidecarSupervisorStatus {
  sidecar_running: boolean;
  sidecar_health?: string | Record<string, unknown>;
  free_ram_gb?: number;
  commit_used_gb?: number;
  commit_total_gb?: number;
  on_ac_power?: boolean;
  profile?: string;
}

export type SidecarProfile = 'dev' | 'prod';

export interface SidecarStartRequest {
  profile: SidecarProfile;
  warm?: boolean;
  force?: boolean;
}

export interface SidecarStartResponse {
  pid: number;
  profile: string;
}

export const adminApi = {
  getStats: () => client.get<PlatformStats>('/admin/stats'),
  listUsers: (skip = 0, limit = 50) =>
    client.get<AdminUser[]>('/admin/users', { params: { skip, limit } }),
  activateUser: (id: string) =>
    client.put<{ message: string }>(`/admin/users/${id}/activate`),
  deactivateUser: (id: string) =>
    client.put<{ message: string }>(`/admin/users/${id}/deactivate`),
  updateRole: (id: string, role: string) =>
    client.put<{ message: string }>(`/admin/users/${id}/role`, { role }),
  terminateSessions: (id: string) =>
    client.post<TerminateSessionsResponse>(`/admin/users/${id}/terminate-sessions`),
  deleteUser: (id: string) =>
    client.delete(`/admin/users/${id}`),
  listAnalyses: (skip = 0, limit = 100) =>
    client.get<AnalysisSummary[]>('/admin/analyses', { params: { skip, limit } }),
  // ── Sidecar supervisor proxy (Task T2/T3) ──────────────────────────────
  getSidecarStatus: () => client.get<SidecarSupervisorStatus>('/admin/sidecar/status'),
  startSidecar: (payload: SidecarStartRequest) =>
    client.post<SidecarStartResponse>('/admin/sidecar/start', payload),
  stopSidecar: () => client.post('/admin/sidecar/stop'),
};
