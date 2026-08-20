/**
 * REAL per-slot payloads, transcribed VERBATIM from the backend.
 *
 * PROVENANCE (MPR1-T09b, 2026-08-15): produced by calling
 * `app.services.tray_messages.slot_verdict` in-process (library code only --
 * no service, no DB, no sidecar) on the frozen tray-contract wells that
 * `dev/backend/tests/test_tray_slots.py` builds (`_well` / `_record` /
 * `_match`), once per `none_route`. The emitter script and its JSON output
 * live outside the repo (session scratchpad); every field below is a
 * character-for-character copy of that output.
 *
 * WHY THIS FILE EXISTS: MPR1-T08 finding 2 showed the tray bars passing on
 * payloads that the backend CANNOT emit -- verify slots hand-written with
 * `terminal: true`, when `slot_verdict` leaves `terminal` false on every
 * verify/reject/abstain/unreadable/error slot. A bar built on an impossible
 * payload is not evidence. Tests must start from these fixtures and override
 * only `slot`/`well` (position), never the state combination itself.
 *
 * THE FULL EMITTED TRUTH TABLE (all nine cases; `none_route` in brackets):
 *   verify              [retry]     occupied t | terminal f | action none
 *   reject              [retry]     occupied t | terminal f | action ask_pharmacist
 *   abstain ask_to_flip [retry]     occupied t | terminal f | action flip_reshoot
 *   unreadable          [retry]     occupied t | terminal f | action flip_reshoot
 *   no_imprint          [retry]     occupied t | terminal f | action flip_reshoot
 *   no_imprint          [terminal]  occupied t | terminal t | action ask_pharmacist
 *   error (well error)  [retry]     occupied t | terminal f | action retry
 *   read_only           [retry]     occupied t | terminal f | action none
 *   empty               [retry]     occupied f | terminal f | action none
 * Note what this table proves: `terminal` is false on EIGHT of the nine, so it
 * cannot be the reshoot trigger. `action === "flip_reshoot"` is.
 */
import type { TraySlot } from '@/types';

const HEDGE = 'Decision-support only -- not a clinical determination. Verify with a pharmacist.';

const BREAKDOWN = {
  S: 0.91,
  colour_score: 1.0,
  imprint_exact: true,
  imprint_fuzzy: 1.0,
  shape_score: 1.0,
  type_score: 1.0,
};

/** The nine slot payloads `slot_verdict` actually emits, at well 0 / slot 1. */
export const REAL_SLOTS = {
  verify: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'verify', action: 'none',
    alert: 'ok', decision: 'verify', abstain_action: null, matched_din: 'DIN13803',
    breakdown: BREAKDOWN, faces_seen: 1, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.slot.verify', params: {}, provisional: true,
      default_en: 'This pill matches one of the medications on your list.',
    },
  },
  reject: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'reject', action: 'ask_pharmacist',
    alert: 'danger', decision: 'reject', abstain_action: null, matched_din: null,
    breakdown: BREAKDOWN, faces_seen: 1, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.slot.reject', params: {}, provisional: true,
      default_en: 'This pill does not match any of the medications on your list. '
        + 'Do not take it. Check with your pharmacist.',
    },
  },
  abstainAskToFlip: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'abstain', action: 'flip_reshoot',
    alert: 'warning', decision: 'abstain', abstain_action: 'ask_to_flip', matched_din: null,
    breakdown: null, faces_seen: 1, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.slot.abstain.ask_to_flip', params: {}, provisional: true,
      default_en: 'MyPillSafe needs to see the other side of this pill. '
        + 'Turn it over and photograph the tray again.',
    },
  },
  unreadable: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'unreadable', action: 'flip_reshoot',
    alert: 'warning', decision: 'abstain', abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 1, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'pill.presence.unreadable', params: { faces_seen: 1, unseen_face_possible: true },
      provisional: false,
      default_en: 'We could not read the markings on this pill. Try another photo, '
        + 'or turn the pill over and photograph the other side.',
    },
  },
  noImprintRetry: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'no_imprint', action: 'flip_reshoot',
    alert: 'warning', decision: 'abstain', abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 2, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.presence.none_retry', params: { faces_seen: 2, slot: 1 }, provisional: true,
      default_en: 'There are no markings on the side of this pill that is facing up. '
        + 'Turn the pill over and photograph the tray again.',
    },
  },
  noImprintTerminal: {
    slot: 1, well: 0, occupied: true, terminal: true, verdict: 'no_imprint', action: 'ask_pharmacist',
    alert: 'warning', decision: 'abstain', abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 2, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'pill.presence.none', params: { faces_seen: 2 }, provisional: false,
      default_en: 'This pill has no markings, so MyPillSafe cannot identify it. '
        + 'Please check with your pharmacist.',
    },
  },
  wellError: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'error', action: 'retry',
    alert: 'warning', decision: null, abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 0, notes: [], pharmacist_hedge: HEDGE,
    error: 'localiser failed on well 0', contract_error: null,
    message: {
      key: 'tray.slot.error', params: { slot: 1 }, provisional: true,
      default_en: 'MyPillSafe could not check this slot. Try photographing the tray again.',
    },
  },
  /** `match=false` was requested, so nothing was checked against the profile.
   * Before the MPR1-T09a backend repair (T08 finding 11) `message` was null
   * and the slot rendered a bare badge; the keyed message below is that
   * repair's emission, re-read from `tray_messages.py` after it landed. */
  readOnly: {
    slot: 1, well: 0, occupied: true, terminal: false, verdict: 'read_only', action: 'none',
    alert: 'info', decision: null, abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 1, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.slot.read_only', params: { slot: 1 }, provisional: true,
      default_en: 'MyPillSafe did not check this pill against your medication list.',
    },
  },
  empty: {
    slot: 1, well: 0, occupied: false, terminal: false, verdict: 'empty', action: 'none',
    alert: 'info', decision: null, abstain_action: null, matched_din: null,
    breakdown: null, faces_seen: 0, notes: [], pharmacist_hedge: HEDGE,
    error: null, contract_error: null,
    message: {
      key: 'tray.slot.empty', params: { slot: 1 }, provisional: true,
      default_en: 'This slot is empty.',
    },
  },
} satisfies Record<string, TraySlot>;

export type RealSlotName = keyof typeof REAL_SLOTS;

/** One real slot, repositioned. Position (`slot`/`well`) is the ONLY thing a
 * test may override -- everything else is what the backend emits. */
export function realSlot(name: RealSlotName, position = 0): TraySlot {
  const base = REAL_SLOTS[name];
  return { ...base, slot: position + 1, well: position };
}

/** The boring happy path the backend really produces: six clean verifies,
 * every one of them `terminal: false`. */
export function sixRealVerifies(): TraySlot[] {
  return Array.from({ length: 6 }, (_, i) => realSlot('verify', i));
}

/** Six real slots with ONE interesting case at position 0. */
export function trayWith(name: RealSlotName): TraySlot[] {
  return [realSlot(name, 0), ...sixRealVerifies().slice(1)];
}
