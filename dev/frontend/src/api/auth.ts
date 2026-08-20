import client from './client';
import type { PendingApprovalResponse, TokenResponse, User } from '@/types';

export interface RegisterPayload {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  preferred_language?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export const authApi = {
  // Two success shapes: 201 + TokenResponse when approval is switched off,
  // 202 + PendingApprovalResponse when it isn't. Both are 2xx, so axios
  // resolves either way — callers must narrow on the status code.
  register: (data: RegisterPayload) =>
    client.post<TokenResponse | PendingApprovalResponse>('/auth/register', data),

  login: (data: LoginPayload) =>
    client.post<TokenResponse>('/auth/login', data),

  logout: () => client.post('/auth/logout'),

  me: () => client.get<User>('/auth/me'),
};
