import { describe, it, expect, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import i18n from '@/i18n';
import { TraySlotGrid } from './TraySlotGrid';
import { TraySlotCard } from './TraySlotCard';
import type { TrayAlertLevel, TraySlot, TraySlotVerdict } from '@/types';
import { realSlot } from '@/test/realTraySlots';

function slot(overrides: Partial<TraySlot>): TraySlot {
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
    matched_din: null,
    breakdown: null,
    pharmacist_hedge: 'Decision-support only -- verify with a pharmacist.',
    error: null,
    contract_error: null,
    ...overrides,
  };
}

/** A full 6-slot grid mixing occupied/empty/error, well 0..5. */
function sixSlots(): TraySlot[] {
  return [
    slot({ slot: 1, well: 0, verdict: 'verify', alert: 'ok' }),
    slot({ slot: 2, well: 1, verdict: 'reject', alert: 'danger', matched_din: null, decision: 'reject' }),
    slot({ slot: 3, well: 2, verdict: 'abstain', alert: 'warning', decision: 'abstain' }),
    slot({ slot: 4, well: 3, occupied: false, terminal: false, verdict: 'empty', alert: 'info', decision: null, pharmacist_hedge: '' }),
    slot({ slot: 5, well: 4, verdict: 'error', alert: 'warning', decision: null, error: 'sidecar 500' }),
    slot({ slot: 6, well: 5, occupied: false, terminal: false, verdict: 'empty', alert: 'info', decision: null, pharmacist_hedge: '' }),
  ];
}

afterEach(async () => {
  await i18n.changeLanguage('en');
});

describe('TraySlotGrid', () => {
  it('bar: renders exactly six slot cards, including the empty and error ones', () => {
    render(<TraySlotGrid slots={sixSlots()} />);
    for (let n = 1; n <= 6; n++) {
      expect(screen.getByTestId(`tray-slot-${n}`)).toBeInTheDocument();
    }
    expect(screen.getAllByTestId(/^tray-slot-/)).toHaveLength(6);
  });

  it('bar: slot number shown is well + 1 (patient-facing "Slot N", not the zero-based well index)', () => {
    render(<TraySlotGrid slots={[slot({ slot: 4, well: 3 })]} />);
    expect(screen.getByTestId('tray-slot-4')).toHaveTextContent('Slot 4');
  });

  it('bar: pharmacist hedge is visible on every non-verify OCCUPIED slot, and absent from the verified one', () => {
    render(<TraySlotGrid slots={sixSlots()} />);
    const verified = screen.getByTestId('tray-slot-1');
    const rejected = screen.getByTestId('tray-slot-2');
    const abstained = screen.getByTestId('tray-slot-3');
    const errored = screen.getByTestId('tray-slot-5');
    expect(within(verified).queryByText(/verify with a pharmacist/i)).not.toBeInTheDocument();
    expect(within(rejected).getByText(/verify with a pharmacist/i)).toBeInTheDocument();
    expect(within(abstained).getByText(/verify with a pharmacist/i)).toBeInTheDocument();
    expect(within(errored).getByText(/verify with a pharmacist/i)).toBeInTheDocument();
  });
});

/** Every verdict the backend can send (`Verdict.ALL`, tray_messages.py) and
 * the `alert` colour level it is paired with in practice -- the card trusts
 * whatever `alert` the slot carries rather than re-deriving one, so this
 * asserts the badge tracks `slot.alert` (colour) and `slot.verdict` (label)
 * independently for the full closed set. */
const VERDICT_CASES: { verdict: TraySlotVerdict; alert: TrayAlertLevel; labelEn: string; labelFr: string }[] = [
  { verdict: 'verify', alert: 'ok', labelEn: 'Verified', labelFr: 'Vérifié' },
  { verdict: 'reject', alert: 'danger', labelEn: "Doesn't Match", labelFr: 'Ne correspond pas' },
  { verdict: 'abstain', alert: 'warning', labelEn: 'Uncertain', labelFr: 'Incertain' },
  { verdict: 'unreadable', alert: 'warning', labelEn: 'Unreadable', labelFr: 'Illisible' },
  { verdict: 'no_imprint', alert: 'warning', labelEn: 'No Markings', labelFr: 'Aucune inscription' },
  { verdict: 'empty', alert: 'info', labelEn: 'Empty', labelFr: 'Vide' },
  { verdict: 'error', alert: 'warning', labelEn: 'Error', labelFr: 'Erreur' },
  { verdict: 'read_only', alert: 'info', labelEn: 'Not Checked', labelFr: 'Non vérifié' },
];

const ALERT_BADGE_CLASS: Record<TrayAlertLevel, string> = {
  ok: 'bg-success-bg',
  warning: 'bg-warning-bg',
  danger: 'bg-danger-bg',
  info: 'bg-blue-50',
};

describe('TraySlotCard verdict -> alert colour / badge mapping (all 8 verdicts, both locales)', () => {
  for (const { verdict, alert, labelEn, labelFr } of VERDICT_CASES) {
    it(`bar: verdict "${verdict}" renders alert "${alert}"'s colour and the "${labelEn}" badge (EN)`, () => {
      render(<TraySlotCard slot={slot({ verdict, alert })} />);
      const badge = screen.getByText(labelEn);
      expect(badge.className).toContain(ALERT_BADGE_CLASS[alert]);
    });

    it(`bar (locale): verdict "${verdict}" renders the "${labelFr}" badge in French`, async () => {
      await i18n.changeLanguage('fr');
      render(<TraySlotCard slot={slot({ verdict, alert })} />);
      const badge = screen.getByText(labelFr);
      expect(badge.className).toContain(ALERT_BADGE_CLASS[alert]);
      await i18n.changeLanguage('en');
    });
  }
});

/** MPR1-T09b, closing T08 finding 11 (frontend half): the `read_only` slot
 * rendered a bare "Not Checked" badge and nothing else. The T09a backend
 * repair gives the slot the PROVISIONAL key `tray.slot.read_only`; this side
 * has to carry that key in BOTH bundles, or a French patient silently gets
 * the English `default_en` fallback. Payload from `@/test/realTraySlots`. */
describe('read_only slot copy (both locales)', () => {
  const READ_ONLY = realSlot('readOnly', 0);

  it('bar: both locale bundles carry copy for the read_only key (no default_en fallback path)', () => {
    for (const lang of ['en', 'fr']) {
      const bundle = i18n.getResourceBundle(lang, 'translation') as { msgCatalog: Record<string, string> };
      expect(bundle.msgCatalog['tray.slot.read_only']).toBeTruthy();
    }
  });

  it('bar: a read_only slot renders a message under its badge, not a bare badge (EN)', () => {
    render(<TraySlotCard slot={READ_ONLY} />);
    const card = screen.getByTestId('tray-slot-1');
    expect(within(card).getByText(i18n.t('trayCheck.verdictLabel.readOnly'))).toBeInTheDocument();
    expect(within(card).getByText(/did not check this pill/i)).toBeInTheDocument();
  });

  it('bar (locale): the same slot renders FRENCH copy, not the English default_en', async () => {
    await i18n.changeLanguage('fr');
    render(<TraySlotCard slot={READ_ONLY} />);
    const card = screen.getByTestId('tray-slot-1');
    const frCopy = (
      i18n.getResourceBundle('fr', 'translation') as { msgCatalog: Record<string, string> }
    ).msgCatalog['tray.slot.read_only'];
    expect(within(card).getByText(frCopy)).toBeInTheDocument();
    expect(within(card).queryByText(READ_ONLY.message!.default_en)).not.toBeInTheDocument();
  });
});

describe('contract_error rendering on the card', () => {
  it('a slot the backend already downgraded (verdict "error") still shows the recheck badge', () => {
    render(
      <TraySlotCard
        slot={slot({
          verdict: 'error',
          alert: 'warning',
          contract_error: 'record: not a C6 record',
          message: { key: 'tray.slot.error.contract', params: null, default_en: 'backend copy', provisional: true },
        })}
      />,
    );
    expect(screen.getByText(/recheck this slot with your pharmacist/i)).toBeInTheDocument();
  });
});
