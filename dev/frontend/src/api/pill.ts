import client from './client';
import type { PillAnalysisV2Response } from '@/types';

export const pillApi = {
  /** `/analyze/pill/v2` -- the only pill-scan endpoint (Phase 3). First call
   * per sidecar process loads models + spawns a Paddle OCR subprocess and
   * can take 30s+; a 180s timeout leaves real headroom above that. */
  analyze: (image: Blob) => {
    const form = new FormData();
    form.append('image', image, 'pill.jpg');
    return client.post<PillAnalysisV2Response>('/analyze/pill/v2', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 180_000,
    });
  },
};
