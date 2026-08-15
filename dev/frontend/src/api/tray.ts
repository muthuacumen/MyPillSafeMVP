import client from './client';
import type { TrayAnalysisResponse, TrayNoneRoute } from '@/types';

export const trayApi = {
  /** `POST /api/v1/tray/analyze` -- one photo of the tray, six per-slot
   * verdicts. Mirrors `pillApi.analyze`'s multipart/timeout idiom; the sidecar
   * call this proxies is timed at 300s server-side (`app/api/v1/routes/tray.py`),
   * so the client timeout leaves headroom above that, same reasoning as the
   * single-pill route's 180s. `none_route` drives the D-4 terminal-after-1-
   * reshoot state machine (`src/lib/trayPageLogic.ts` picks it, this client
   * just forwards it) -- default 'retry' matches the backend's own default. */
  analyze: (image: Blob, noneRoute: TrayNoneRoute = 'retry') => {
    const form = new FormData();
    form.append('photo', image, 'tray.jpg');
    form.append('none_route', noneRoute);
    return client.post<TrayAnalysisResponse>('/tray/analyze', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 305_000,
    });
  },
};
