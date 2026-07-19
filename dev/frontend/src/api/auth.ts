import client from './client';
import type { TokenResponse, User } from '@/types';

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
  register: (data: RegisterPayload) =>
    client.post<TokenResponse>('/auth/register', data),

  login: (data: LoginPayload) =>
    client.post<TokenResponse>('/auth/login', data),

  logout: () => client.post('/auth/logout'),

  me: () => client.get<User>('/auth/me'),
};
