/**
 * Extracts a verbatim, human-readable message from a failed axios request
 * against this backend.
 *
 * FOUR DIFFERENT error-body shapes exist across the admin API surface, and a
 * caller must not assume just one:
 *
 *  1. Routes that raise `HTTPException(detail={"error": {"code",
 *     "message"}})` -- the auth/admin dependencies in
 *     `app/api/deps.py`, `/admin/users/*` in
 *     `app/api/v1/routes/admin.py`, and the sidecar proxy's own
 *     `_unreachable()` 502 (`SUPERVISOR_UNAVAILABLE`) -- get wrapped by
 *     FastAPI as `{"detail": {"error": {"code", "message"}}}`. `detail.error`
 *     is an OBJECT here.
 *
 *  2. The sidecar Supervisor's (`ops/supervisor/supervisor.py`) plain,
 *     unstructured refusals -- already-running, the free-RAM floor, the
 *     on-battery guard, "nothing listening on port 8100" -- raise
 *     `HTTPException(detail="<plain text>")`. The backend's
 *     `_passthrough()` (`admin_sidecar.py`) forwards the Supervisor's own
 *     FastAPI-serialized body verbatim, so this arrives as
 *     `{"detail": "<plain text>"}` -- `detail` is a STRING.
 *
 *  3. The Supervisor's STRUCTURED refusals (`start_in_progress`,
 *     `foreign_process_on_port`, `kill_incomplete`) raise
 *     `HTTPException(detail={"error": "<code>", "message": "<text>", ...})`
 *     -- `error` here is a STRING code, not an object, with the actionable
 *     text on a sibling `message` key. The Supervisor's own FastAPI wraps
 *     that as `{"detail": {"error": "<code>", "message": "<text>", ...}}`
 *     before `_passthrough()` forwards it unchanged.
 *
 *  4. If the Supervisor ever answers with a body `_passthrough()` can't
 *     parse as JSON, it builds a fallback body itself and returns it as a
 *     raw `JSONResponse` (not a raised `HTTPException`):
 *     `{"error": {"code": "SUPERVISOR_INVALID_RESPONSE", "message":
 *     response.text}}` -- with NO "detail" wrapper at all.
 *
 * This helper checks all four shapes so a guard-refused 422, an
 * already-running 409, or a structured Supervisor refusal surfaces its real
 * message either way -- never masked behind a generic fallback.
 */
export function extractApiErrorMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: unknown } })?.response?.data as
    | {
        detail?:
          | { error?: { message?: string } | string; message?: string }
          | string;
        error?: { message?: string };
      }
    | undefined;

  if (!data) return fallback;
  if (typeof data.detail === 'string') return data.detail;

  if (data.detail && typeof data.detail === 'object') {
    const { error, message } = data.detail;
    // Shape 3: `error` is the string code, actionable text is the sibling
    // `message` key -- fall back to the code itself if `message` is absent.
    if (typeof error === 'string') return message ?? error;
    // Shape 1: `error` is the {code, message} object.
    if (error?.message) return error.message;
  }

  // Shape 4: no "detail" wrapper at all.
  return data.error?.message ?? fallback;
}
