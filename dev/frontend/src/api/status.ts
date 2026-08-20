import client from './client';

/** `GET /status/sidecar` (Task T2, `dev/backend/app/api/v1/routes/status.py`)
 * -- NO auth, meant to be polled by the SidecarTicker on every page. Backend
 * caches this for 20s server-side, so polling it is cheap. */
export interface PublicSidecarStatus {
  sidecar_up: boolean;
  message: string;
  checked_at: string;
}

export const statusApi = {
  getSidecarStatus: () => client.get<PublicSidecarStatus>('/status/sidecar'),
};
