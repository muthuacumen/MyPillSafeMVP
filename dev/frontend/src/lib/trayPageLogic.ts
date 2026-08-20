import type { TFunction } from 'i18next';
import type { TraySlot, TrayNoneRoute } from '@/types';

/** D-4 (Muthu, 2026-08-14): terminal-after-1-reshoot. Attempt 1 always calls
 * with `none_route="retry"`; the one allowed reshoot (attempt 2) calls with
 * `none_route="terminal"`, after which the session is done regardless of
 * what any individual slot still says -- see `needsReshoot` below, which is
 * only ever consulted for an attempt-1 response. */
export type TrayAttempt = 1 | 2;

export function noneRouteForAttempt(attempt: TrayAttempt): TrayNoneRoute {
  return attempt === 1 ? 'retry' : 'terminal';
}

/** The one backend field that means "photograph the tray again": the C.6
 * ACTION. `tray_messages.py::Action.FLIP_RESHOOT` is set on exactly three
 * emissions -- a no_imprint slot under the retry route, an unreadable slot,
 * and an abstain/ask_to_flip slot -- and on nothing else. */
const RESHOOT_ACTION = 'flip_reshoot';

/** True when at least one occupied slot is ASKING for a reshoot, i.e. carries
 * `action === "flip_reshoot"` and has not already been spent (`terminal`).
 *
 * KEYED ON `action`, NOT ON `terminal` (MPR1-T09b, closing T08 finding 2).
 * The old test `s.occupied && !s.terminal` read `terminal` as "this slot is
 * resolved", which it is not: `slot_verdict` leaves `terminal` FALSE on every
 * verify, reject, abstain, unreadable, error and read_only slot -- only the
 * no_imprint/TERMINAL route and the scope fallback ever set it true. So a
 * perfect tray of six verified pills satisfied the old predicate and the page
 * demanded a reshoot after a flawless scan, contradicting D-4 (the prompt is
 * for the flip cases). `terminal` survives here only in its real meaning: a
 * slot that already had its one allowed reshoot cannot ask for another.
 *
 * Only meaningful for an ATTEMPT-1 response: the page caps the loop at one
 * reshoot no matter what this returns for an attempt-2 response. */
export function needsReshoot(slots: TraySlot[]): boolean {
  return slots.some((s) => s.occupied && s.action === RESHOOT_ACTION && !s.terminal);
}

export interface TrayApiErrorInfo {
  status?: number;
  code?: string;
  /** This app's OWN structured message, when its route sent one -- preferred
   * over generic copy (mirrors AnalyzePage's `resolveErrorMessage`). */
  serverMessage?: string;
  /** The SIDECAR's frame-level body, which is a bare string, not an object:
   * `{"error": "unreadable image: <path>"}` (recorded verbatim in
   * `results/nb08_tray_route/run1/contract_check.json`). Parsed so the shape
   * is recognised rather than silently dropped, but deliberately NOT rendered
   * -- see `resolveTrayApiError`. */
  sidecarDetail?: string;
}

/** Unwraps an axios rejection into the shapes a tray-route error really takes.
 *
 * 1. `{"detail": {"error": {code, message}}}` -- an `HTTPException(detail=...)`
 *    from THIS app's own route (501/422/503), wrapped by FastAPI.
 * 2. `{"error": "<string>"}` -- the SIDECAR's frame-level 4xx, which
 *    `routes/tray.py` passes through verbatim via `JSONResponse`. This is the
 *    shape the recorded contract check actually captured; the earlier bar
 *    asserted a `{code, message}` object here that no producer emits
 *    (MPR1-T08 finding 7), so the app fell through to generic copy while the
 *    bar claimed the server message was preferred.
 * 3. `{"error": {code, message}}` -- kept as a defensive third branch for a
 *    future structured passthrough; nothing emits it today.
 *
 * An unrecognised shape yields no code/message and the caller falls back to
 * generic copy. */
export function extractTrayApiError(err: unknown): TrayApiErrorInfo {
  const response = (
    err as {
      response?: {
        status?: number;
        data?: {
          error?: string | { code?: string; message?: string };
          detail?: { error?: { code?: string; message?: string } };
        };
      };
    }
  )?.response;
  const data = response?.data;
  const topLevel = data?.error;
  const structured = data?.detail?.error ?? (typeof topLevel === 'object' ? topLevel : undefined);
  return {
    status: response?.status,
    code: structured?.code,
    serverMessage: structured?.message,
    sidecarDetail: typeof topLevel === 'string' ? topLevel : undefined,
  };
}

/** Resolves a caught `trayApi.analyze` rejection to display copy. Mirrors
 * AnalyzePage's `resolveErrorMessage` split (sidecar-down vs backend-down vs
 * genuine bad-photo outcome), plus the tray route's two tray-specific codes
 * (`TRAY_ANALYZE_DISABLED` 501, `TRAY_BAD_NONE_ROUTE` 422) that the
 * single-pill route does not have. */
export function resolveTrayApiError(err: unknown, t: TFunction): string {
  const { status, code, serverMessage } = extractTrayApiError(err);
  // CODE first, and exclusively for TRAY_BAD_NONE_ROUTE: it shares its 422
  // status with any sidecar frame-level 4xx passthrough, which is a
  // completely different (sidecar-owned) failure that must fall through to
  // the server-message-preferring branch below, not be misread as this app's
  // own bad-parameter response just because the status number matches.
  if (code === 'TRAY_ANALYZE_DISABLED') return t('trayCheck.error.disabled');
  if (code === 'TRAY_BAD_NONE_ROUTE') return t('trayCheck.error.badNoneRoute');
  if (code === 'BRAINS_UNAVAILABLE' || code === 'OCR_UNAVAILABLE') return t('trayCheck.error.brainsUnavailable');
  // No recognised app-owned code -- 501 and 503 are safe to bare-status-match
  // because this route has no OTHER way to raise them (unlike 422).
  if (status === 501) return t('trayCheck.error.disabled');
  if (status === 503) return t('trayCheck.error.brainsUnavailable');
  if (status !== undefined && status >= 500) return t('trayCheck.error.serverGeneric');
  // Genuine per-frame rejection (4xx from the sidecar, or no response at all).
  // This app's OWN structured message is patient-facing copy and is preferred;
  // the sidecar's bare-string body (`sidecarDetail`) is NOT rendered. It is
  // English-only diagnostic text and, as recorded in `contract_check.json`, it
  // can carry a server filesystem path ("unreadable image: C:\Users\...\tmpX.jpg")
  // -- MPR1-T08 finding 8. The localised retake guidance below is both safer
  // and more useful to the patient than that string; the raw value stays on
  // `TrayApiErrorInfo.sidecarDetail` for a caller that wants to log it.
  return serverMessage ?? t('trayCheck.error.default');
}
