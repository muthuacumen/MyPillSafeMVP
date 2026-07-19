import client from './client';
import type { DinSuggestion } from '@/types';

/** Thin authenticated proxy to the brains sidecar's DIN reference search
 * (`GET /api/v1/reference/search` -> sidecar `/reference/search`). The
 * browser never talks to the sidecar directly. */
export const referenceApi = {
  search: (q: string, limit = 8) =>
    client.get<DinSuggestion[]>('/reference/search', { params: { q, limit } }),
};
