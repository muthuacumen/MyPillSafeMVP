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
  deleteUser: (id: string) =>
    client.delete(`/admin/users/${id}`),
  listAnalyses: (skip = 0, limit = 100) =>
    client.get<AnalysisSummary[]>('/admin/analyses', { params: { skip, limit } }),
};
