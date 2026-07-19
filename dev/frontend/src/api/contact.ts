import client from './client';

export interface ContactPayload {
  full_name: string;
  email: string;
  message: string;
}

export const contactApi = {
  submit: (payload: ContactPayload) => client.post<{ message: string }>('/contact', payload),
};
