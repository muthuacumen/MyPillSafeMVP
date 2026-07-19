import client from './client';
import type { Patient } from '@/types';

export interface PatientUpdatePayload {
  first_name?: string;
  last_name?: string;
  phone_number?: string | null;
  preferred_language?: string;
  notifications_enabled?: boolean;
}

export const patientsApi = {
  me: () => client.get<Patient>('/patients/me'),
  update: (payload: PatientUpdatePayload) => client.patch<Patient>('/patients/me', payload),
  changePassword: (current_password: string, new_password: string) =>
    client.patch('/patients/me/password', { current_password, new_password }),
  deleteAccount: () => client.delete('/patients/me'),
};
