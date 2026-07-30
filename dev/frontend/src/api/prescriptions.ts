import client from './client';
import type { ParseFlag, Prescription, PrescriptionWithSuggestions, ReviewStatus } from '@/types';

/** PATCH body. `review_status: 'approved'` is the explicit approve action;
 * `confirmed_flags` carries the guardrail flags the user ticked off in the
 * review screen, which the backend requires before it will approve a
 * medication that carries a blocking flag. */
export type PrescriptionUpdatePayload = Partial<Prescription> & {
  review_status?: ReviewStatus;
  confirmed_flags?: ParseFlag[];
};

export const prescriptionsApi = {
  upload: (image: Blob) => {
    const form = new FormData();
    form.append('image', image, 'prescription.jpg');
    // FixbySonnet1 Task 4b: the shared `client` instance has no default
    // timeout (infinite) -- explicit here so a hung request eventually
    // surfaces as an error instead of spinning forever. OCR itself can
    // legitimately take a couple of minutes on CPU; generous headroom above
    // that, matching pillApi's 180s pattern but for the slower Rx OCR path.
    return client.post<PrescriptionWithSuggestions[]>('/prescriptions', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 330_000,
    });
  },

  /** Every active medication, pending proposals included -- what the review
   * screen needs. */
  listMine: () => client.get<Prescription[]>('/prescriptions/me'),

  /** APPROVED medications only. Every schedule-bearing surface (the
   * dashboard's today's-doses list, the dose-reminder engine) must use this
   * one: an unapproved proposal may never generate a reminder. */
  listApproved: () =>
    client.get<Prescription[]>('/prescriptions/me', { params: { review_status: 'approved' } }),

  update: (id: string, payload: PrescriptionUpdatePayload) =>
    client.patch<Prescription>(`/prescriptions/${id}`, payload),

  remove: (id: string) => client.delete(`/prescriptions/${id}`),

  getImageBlob: (id: string) =>
    client.get<Blob>(`/prescriptions/${id}/image`, { responseType: 'blob' }),
};
