import { describe, it, expect } from 'vitest';
import { applyContractErrorGuard, CONTRACT_ERROR_GUARD_KEY } from './trayContractGuard';
import type { TraySlot } from '@/types';

function baseSlot(overrides: Partial<TraySlot>): TraySlot {
  return {
    slot: 1,
    well: 0,
    occupied: true,
    terminal: true,
    message: null,
    notes: [],
    faces_seen: 1,
    verdict: 'verify',
    action: 'none',
    alert: 'ok',
    decision: 'verify',
    abstain_action: null,
    matched_din: '00013803',
    breakdown: { S: 0.98 },
    pharmacist_hedge: 'Decision-support only.',
    error: null,
    contract_error: null,
    ...overrides,
  };
}

describe('applyContractErrorGuard (D-7 defense-in-depth)', () => {
  it('bar: contract_error + verdict "verify" (should be impossible post-D-7) is downgraded to the error/recheck state', () => {
    const malformed = baseSlot({ contract_error: 'record: not a C6 record', verdict: 'verify' });
    const guarded = applyContractErrorGuard(malformed);

    expect(guarded.verdict).toBe('error');
    expect(guarded.alert).toBe('warning');
    expect(guarded.action).toBe('ask_pharmacist');
    expect(guarded.matched_din).toBeNull();
    expect(guarded.breakdown).toBeNull();
    expect(guarded.message?.key).toBe(CONTRACT_ERROR_GUARD_KEY);
    expect(guarded.message?.default_en).toMatch(/pharmacist/i);
  });

  it('a slot already carrying verdict "error" from the backend\'s own D-7 downgrade passes through unchanged (not double-guarded)', () => {
    const alreadyDowngraded = baseSlot({
      contract_error: 'record: not a C6 record',
      verdict: 'error',
      action: 'ask_pharmacist',
      alert: 'warning',
      matched_din: null,
      breakdown: null,
      message: { key: 'tray.slot.error.contract', params: null, default_en: 'backend copy', provisional: true },
    });
    const guarded = applyContractErrorGuard(alreadyDowngraded);
    expect(guarded).toBe(alreadyDowngraded); // same reference -- no-op
    expect(guarded.message?.key).toBe('tray.slot.error.contract');
  });

  it('a normal slot with no contract_error is untouched', () => {
    const clean = baseSlot({ contract_error: null, verdict: 'verify' });
    expect(applyContractErrorGuard(clean)).toBe(clean);
  });
});
