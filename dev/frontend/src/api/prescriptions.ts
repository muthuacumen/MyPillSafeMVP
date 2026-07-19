import client from './client';
import type { Prescription, PrescriptionWithSuggestions } from '@/types';

export const prescriptionsApi = {
  upload: (image: Blob) => {
    const form = new FormData();
    form.append('image', image, 'prescription.jpg');
    return client.post<PrescriptionWithSuggestions[]>('/prescriptions', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  listMine: () => client.get<Prescription[]>('/prescriptions/me'),

  update: (id: string, payload: Partial<Prescription>) =>
    client.patch<Prescription>(`/prescriptions/${id}`, payload),

  remove: (id: string) => client.delete(`/prescriptions/${id}`),

  getImageBlob: (id: string) =>
    client.get<Blob>(`/prescriptions/${id}/image`, { responseType: 'blob' }),
};
