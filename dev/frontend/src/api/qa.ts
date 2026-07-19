import client from './client';
import type { QAChatResponse } from '@/types';

export interface QAChatParams {
  message: string;
  /** Canonical 8-digit DIN bypass -- only for confirmed DINs (a linked
   * medication card, or a just-verified pill scan's matched_din). */
  din?: string;
  /** Pass on the turn AFTER a status="confirm" response, once the user has
   * tapped "Yes, I meant X" -- never auto-passed. */
  confirmed_name?: string;
  language?: string;
}

export const qaApi = {
  /** `/api/v1/qa/chat` -- CB4 (cloud) when a key is configured server-side,
   * otherwise the sidecar's offline local-7B fallback. Generation can take
   * several seconds either way; a generous timeout leaves headroom above
   * the sidecar's own 60s (context mode) / 180s (offline fallback) budget. */
  chat: (params: QAChatParams) =>
    client.post<QAChatResponse>('/qa/chat', params, { timeout: 190_000 }),
};
