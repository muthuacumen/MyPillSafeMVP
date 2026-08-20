import { describe, it, expect } from 'vitest';
import { extractApiErrorMessage } from './apiError';

// Bodies below are copied verbatim from the real request/response shapes,
// not idealized ones -- see:
//   - `Production/PillSafe/dev/backend/app/api/deps.py`
//   - `Production/PillSafe/dev/backend/app/api/v1/routes/admin.py`
//   - `Production/PillSafe/dev/backend/app/api/v1/routes/admin_sidecar.py`
//   - `Production/ops/supervisor/supervisor.py`

function axiosError(status: number, data: unknown) {
  return { response: { status, data } };
}

const FALLBACK = 'could not reach the sidecar admin API';

describe('extractApiErrorMessage', () => {
  it('shape 1: backend HTTPException(detail={"error": {"code","message"}}) -- nested object', () => {
    // admin_sidecar.py _unreachable(): 502 SUPERVISOR_UNAVAILABLE
    const body = {
      detail: {
        error: {
          code: 'SUPERVISOR_UNAVAILABLE',
          message:
            'The sidecar supervisor could not be reached at http://127.0.0.1:8090. Make sure it is running.',
        },
      },
    };
    expect(extractApiErrorMessage(axiosError(502, body), FALLBACK)).toBe(
      'The sidecar supervisor could not be reached at http://127.0.0.1:8090. Make sure it is running.',
    );

    // admin.py _404, reused across /admin/users/{id}/activate|deactivate etc.
    const notFound = { detail: { error: { code: 'NOT_FOUND', message: 'User not found.' } } };
    expect(extractApiErrorMessage(axiosError(404, notFound), FALLBACK)).toBe('User not found.');
  });

  it('shape 2: Supervisor plain-string HTTPException detail, passed through verbatim', () => {
    // supervisor.py POST /start: free-RAM floor guard (422) -- unconditional,
    // force does not bypass it.
    const ramGuard = {
      detail:
        'free RAM 1.70 GB is below the SUPERVISOR_MIN_FREE_GB floor (3.0 GB) -- ' +
        'refusing to launch (Futureworks #35: WinError 1455 under memory pressure)',
    };
    expect(extractApiErrorMessage(axiosError(422, ramGuard), FALLBACK)).toBe(
      'free RAM 1.70 GB is below the SUPERVISOR_MIN_FREE_GB floor (3.0 GB) -- ' +
        'refusing to launch (Futureworks #35: WinError 1455 under memory pressure)',
    );

    // supervisor.py POST /start: on-battery guard (422), force=false.
    const batteryGuard = {
      detail:
        'running on battery power and force=false -- battery starts have misbehaved ' +
        'before (owner-measured); pass force=true to override',
    };
    expect(extractApiErrorMessage(axiosError(422, batteryGuard), FALLBACK)).toBe(
      'running on battery power and force=false -- battery starts have misbehaved ' +
        'before (owner-measured); pass force=true to override',
    );
  });

  it('shape 3: Supervisor structured refusal -- detail.error is a STRING code, message is a sibling key', () => {
    // supervisor.py POST /start: 409 start_in_progress.
    const startInProgress = {
      detail: {
        error: 'start_in_progress',
        message:
          'a start is already in flight (pid 4242, profile dev) -- wait for it to finish ' +
          'or fail before starting another',
        pid: 4242,
        profile: 'dev',
      },
    };
    expect(extractApiErrorMessage(axiosError(409, startInProgress), FALLBACK)).toBe(
      'a start is already in flight (pid 4242, profile dev) -- wait for it to finish ' +
        'or fail before starting another',
    );

    // supervisor.py POST /stop: 409 foreign_process_on_port.
    const foreignProcess = {
      detail: {
        error: 'foreign_process_on_port',
        message:
          'pid 9999 is listening on port 8100 but does not match the sidecar\'s expected ' +
          'signature (venv python exe or a uvicorn/app:app command line) -- refusing to ' +
          'kill a process this supervisor did not start',
        pid: 9999,
        exe: null,
        cmdline: 'python -m http.server 8100',
      },
    };
    expect(extractApiErrorMessage(axiosError(409, foreignProcess), FALLBACK)).toBe(
      "pid 9999 is listening on port 8100 but does not match the sidecar's expected " +
        'signature (venv python exe or a uvicorn/app:app command line) -- refusing to ' +
        'kill a process this supervisor did not start',
    );

    // supervisor.py POST /stop: 409 kill_incomplete.
    const killIncomplete = {
      detail: {
        error: 'kill_incomplete',
        message:
          'one or more processes in the sidecar\'s tree could not be terminated ' +
          '(permission denied or already a zombie) -- check manually',
        pid: 4242,
        failures: [{ pid: 4243, stage: 'terminate', error: 'AccessDenied()' }],
      },
    };
    expect(extractApiErrorMessage(axiosError(409, killIncomplete), FALLBACK)).toBe(
      "one or more processes in the sidecar's tree could not be terminated " +
        '(permission denied or already a zombie) -- check manually',
    );

    // Defensive: falls back to the code string itself if `message` were absent.
    const noMessage = { detail: { error: 'start_in_progress' } };
    expect(extractApiErrorMessage(axiosError(409, noMessage), FALLBACK)).toBe('start_in_progress');
  });

  it('shape 4: no "detail" wrapper -- _passthrough()\'s non-JSON-response fallback', () => {
    // admin_sidecar.py _passthrough(): response.json() raised ValueError.
    const invalidResponse = {
      error: {
        code: 'SUPERVISOR_INVALID_RESPONSE',
        message: 'Internal Server Error',
      },
    };
    expect(extractApiErrorMessage(axiosError(500, invalidResponse), FALLBACK)).toBe(
      'Internal Server Error',
    );
  });

  it('falls back to the caller-supplied fallback when no known shape matches', () => {
    expect(extractApiErrorMessage(axiosError(500, {}), FALLBACK)).toBe(FALLBACK);
    expect(extractApiErrorMessage(axiosError(500, { detail: {} }), FALLBACK)).toBe(FALLBACK);
    expect(extractApiErrorMessage(new Error('network error'), FALLBACK)).toBe(FALLBACK);
    expect(extractApiErrorMessage(undefined, FALLBACK)).toBe(FALLBACK);
  });
});
