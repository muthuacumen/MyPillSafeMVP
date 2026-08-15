import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { isTrayCheckEnabled } from '@/lib/featureFlags';

/** Route guard for the MPR1 tray-check page. With `VITE_TRAY_CHECK` unset (the
 * default) the path behaves as if the feature did not exist: the deep link
 * redirects to the dashboard instead of rendering a page that would call a
 * `/tray/analyze` endpoint the production sidecar does not serve. Hiding the
 * nav entry alone would not do -- the URL is guessable and bookmarkable.
 *
 * The flag is read on RENDER (not at module load) so the guard reflects the
 * environment the app is actually running in. */
export function RequireTrayCheck({ children }: { children: ReactNode }) {
  return isTrayCheckEnabled() ? <>{children}</> : <Navigate to="/dashboard" replace />;
}
