import type { TraySlot } from '@/types';

/** The frontend-owned message key for the guard's own fabricated copy --
 * wired into `msgCatalog` in i18n/locales/{en,fr}.json like every other tray
 * message, so `TraySlotCard` can render it through the exact same
 * `resolveTrayMsg` path as a backend-authored one. */
export const CONTRACT_ERROR_GUARD_KEY = 'frontend.trayGuard.contractError';

const GUARD_DEFAULT_EN =
  'This slot could not be safely checked, so its result is not being shown. ' +
  'Recheck this slot with your pharmacist.';

/**
 * D-7 (Muthu, 2026-08-14, MPR1 `_INDEX.md`): a slot the backend could not
 * validate against the C6 record contract must NEVER reach the patient as a
 * green "verify". The backend enforces this itself, uniformly, in
 * `app/services/tray_messages.py::slot_verdict` (the `if contract_error:`
 * branch runs before any decision branch and always sets `verdict="error"`).
 *
 * This is the frontend's DEFENSE-IN-DEPTH for the "should be impossible
 * post-D-7" case: a slot arrives with `contract_error` set but a `verdict`
 * other than `"error"` anyway (a stale/misconfigured backend deploy, a mocked
 * response in a test, a future regression). Scoped to `verdict !== "error"`
 * rather than `verdict === "verify"` only, so it also catches a malformed
 * slot claiming `reject`/`abstain`/etc alongside a contract error -- any such
 * combination is equally "should be impossible" under D-7's own rule, and the
 * one condition the brief called out (`verify` + `contract_error`) is the
 * headline case this covers, not the only one. Flagged in the T07 report.
 *
 * ONE function, on purpose: the day Muthu's ruling on this changes, this is
 * the only place to edit.
 *
 * When it fires: verdict -> "error", alert -> "warning", action ->
 * "ask_pharmacist" (mirrors the backend's own contract-error branch exactly),
 * `matched_din`/`breakdown` withheld (same withholding rule the backend
 * already applies whenever a message-owning layer, not SB2's identification,
 * is what the patient is shown), and `message` replaced with a neutral,
 * translated recheck notice -- deliberately generic copy, since a frontend
 * guard firing at all means the original message is not trusted either.
 */
export function applyContractErrorGuard(slot: TraySlot): TraySlot {
  if (!slot.contract_error || slot.verdict === 'error') return slot;
  return {
    ...slot,
    verdict: 'error',
    alert: 'warning',
    action: 'ask_pharmacist',
    matched_din: null,
    breakdown: null,
    message: {
      key: CONTRACT_ERROR_GUARD_KEY,
      params: null,
      default_en: GUARD_DEFAULT_EN,
      provisional: true,
    },
  };
}
