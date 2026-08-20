import { describe, it, expect } from 'vitest';
import type { TFunction } from 'i18next';
import { extractTrayApiError, needsReshoot, noneRouteForAttempt, resolveTrayApiError } from './trayPageLogic';
import { realSlot, sixRealVerifies, trayWith } from '@/test/realTraySlots';

// A `t` stub that returns the key itself -- enough to assert routing without
// depending on the real locale bundles (those are covered by trayMessages.test.ts
// and the component-level tests).
const t = ((key: string) => key) as TFunction;

describe('noneRouteForAttempt (D-4 attempt -> request parameter)', () => {
  it('attempt 1 sends "retry"', () => {
    expect(noneRouteForAttempt(1)).toBe('retry');
  });
  it('attempt 2 sends "terminal"', () => {
    expect(noneRouteForAttempt(2)).toBe('terminal');
  });
});

/** Every payload below comes from `@/test/realTraySlots` -- the backend's own
 * `slot_verdict` output, not a hand-built state combination (MPR1-T08 finding
 * 2: the previous bars asserted on verify slots with `terminal: true`, which
 * the backend never emits). */
describe('needsReshoot (D-4, keyed on the backend `action` field)', () => {
  it('bar (a): SIX CLEAN VERIFIES -- every one terminal:false, as the backend really emits -- ask for NO reshoot', () => {
    expect(needsReshoot(sixRealVerifies())).toBe(false);
  });

  it('bar (b): one no_imprint retry slot (action flip_reshoot) offers the reshoot', () => {
    expect(needsReshoot(trayWith('noImprintRetry'))).toBe(true);
  });

  it('bar (c): the attempt-2 terminal no_imprint slot (action ask_pharmacist) does NOT ask again', () => {
    expect(needsReshoot(trayWith('noImprintTerminal'))).toBe(false);
  });

  it('bar (d): an unreadable slot offers the reshoot -- it carries action flip_reshoot', () => {
    expect(needsReshoot(trayWith('unreadable'))).toBe(true);
  });

  it('an abstain/ask_to_flip slot offers the reshoot (same action, different verdict)', () => {
    expect(needsReshoot(trayWith('abstainAskToFlip'))).toBe(true);
  });

  it('a rejected slot is an ANSWER, not a reshoot: terminal:false but action ask_pharmacist', () => {
    expect(needsReshoot(trayWith('reject'))).toBe(false);
  });

  it('an errored well says "retry the whole photo", not "flip this pill" -- no reshoot prompt', () => {
    expect(needsReshoot(trayWith('wellError'))).toBe(false);
  });

  it('an empty well never triggers a reshoot', () => {
    expect(needsReshoot([realSlot('empty', 0)])).toBe(false);
  });

  it('an UNOCCUPIED slot is ignored even if something else set flip_reshoot on it', () => {
    const ghost = { ...realSlot('noImprintRetry', 0), occupied: false };
    expect(needsReshoot([ghost])).toBe(false);
  });

  it('a flip_reshoot slot that is already terminal is spent -- no further prompt', () => {
    const spent = { ...realSlot('noImprintRetry', 0), terminal: true };
    expect(needsReshoot([spent])).toBe(false);
  });
});

describe('resolveTrayApiError', () => {
  it('bar: 501 TRAY_ANALYZE_DISABLED renders the disabled-server copy', () => {
    const err = { response: { status: 501, data: { detail: { error: { code: 'TRAY_ANALYZE_DISABLED', message: 'x' } } } } };
    expect(resolveTrayApiError(err, t)).toBe('trayCheck.error.disabled');
  });

  it('bar: 503 BRAINS_UNAVAILABLE renders the sidecar-down copy, distinct from a generic 500', () => {
    const err = { response: { status: 503, data: { detail: { error: { code: 'BRAINS_UNAVAILABLE', message: 'x' } } } } };
    expect(resolveTrayApiError(err, t)).toBe('trayCheck.error.brainsUnavailable');
  });

  it('422 TRAY_BAD_NONE_ROUTE renders its own copy, not the generic server error', () => {
    const err = { response: { status: 422, data: { detail: { error: { code: 'TRAY_BAD_NONE_ROUTE', message: 'x' } } } } };
    expect(resolveTrayApiError(err, t)).toBe('trayCheck.error.badNoneRoute');
  });

  // The REAL recorded sidecar frame-level 4xx, copied byte-for-byte out of
  // `IMB1_Prototype/NB08_Notebook/results/nb08_tray_route/run1/contract_check.json`
  // ("frame_level": {"http": 422, "body": {"error": "unreadable image: ..."}}).
  // `routes/tray.py` passes that body through verbatim, so this -- not the
  // {code, message} object the old bar invented -- is what the browser sees.
  const REAL_SIDECAR_4XX = {
    response: {
      status: 422,
      data: { error: 'unreadable image: C:\\Users\\muthu\\AppData\\Local\\Temp\\tmpgu2rqezs.jpg' },
    },
  };

  it('bar: the REAL sidecar 4xx shape ({"error": "<string>"}) is parsed, not silently unrecognised', () => {
    const info = extractTrayApiError(REAL_SIDECAR_4XX);
    expect(info.status).toBe(422);
    expect(info.sidecarDetail).toBe(
      'unreadable image: C:\\Users\\muthu\\AppData\\Local\\Temp\\tmpgu2rqezs.jpg',
    );
    expect(info.code).toBeUndefined();
  });

  it('bar: the REAL sidecar 4xx renders localised retake copy and NEVER the raw server string', () => {
    const shown = resolveTrayApiError(REAL_SIDECAR_4XX, t);
    expect(shown).toBe('trayCheck.error.default');
    expect(shown).not.toContain('AppData');
    expect(shown).not.toContain('unreadable image');
  });

  it('defensive: a {code, message} object at the top level still parses (no producer emits it today)', () => {
    const err = { response: { status: 422, data: { error: { code: 'SOME_CODE', message: 'sidecar said no' } } } };
    expect(extractTrayApiError(err).serverMessage).toBe('sidecar said no');
  });

  it('a bare 500 with no known code renders the generic server-error copy', () => {
    const err = { response: { status: 500, data: {} } };
    expect(resolveTrayApiError(err, t)).toBe('trayCheck.error.serverGeneric');
  });

  it('no response at all (network failure) falls back to the default tray copy', () => {
    expect(resolveTrayApiError(new Error('network down'), t)).toBe('trayCheck.error.default');
  });
});
