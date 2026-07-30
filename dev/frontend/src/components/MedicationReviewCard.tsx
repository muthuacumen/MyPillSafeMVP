import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AlertTriangle, CheckCircle2, Clock4, Plus, ShieldAlert, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { DinLinkPanel } from '@/components/DinLinkPanel';
import { prescriptionsApi } from '@/api/prescriptions';
import { BLOCKING_PARSE_FLAGS, type DinSuggestion, type ParseFlag, type Prescription } from '@/types';

/** Frequencies the user can choose from. Mirrors the backend guardrail enum
 * (`app/services/rx_guardrails.py: FREQUENCY_ENUM`) exactly. */
const FREQUENCIES = [
  'ONCE_DAILY', 'BID', 'TID', 'QID', 'BEDTIME', 'WITH_MEALS',
  'PRN', 'WEEKLY', 'EVERY_N_HOURS', 'TAPER', 'UNKNOWN',
] as const;

/** The backend's canonical derivation table, mirrored here for ONE purpose:
 * offering the user a suggested schedule as a visible CHOICE they must tap.
 * These are never prefilled into a medication that has no times -- the whole
 * point of the redesign is that the app stops inventing 08:00. */
const SUGGESTED_TIMES: Record<string, string[]> = {
  ONCE_DAILY: ['08:00'],
  BID: ['08:00', '18:00'],
  TID: ['08:00', '13:00', '18:00'],
  QID: ['08:00', '13:00', '18:00', '21:00'],
  BEDTIME: ['21:00'],
  WITH_MEALS: ['08:00', '13:00', '18:00'],
};

interface MedicationReviewCardProps {
  prescription: Prescription;
  /** Fired with the server's updated row after a successful approve. */
  onApproved: (updated: Prescription) => void;
  /** Optional DIN-confirm hook; when omitted the DIN panel is not offered. */
  onDinConfirmed?: (din: string) => Promise<void> | void;
  /** Suggestions already fetched at scan time, so the DIN panel does not
   * re-query for something the create response already carried. */
  initialDinSuggestions?: DinSuggestion[];
}

/**
 * FixbyOPUS3 Task A4 -- the review/edit/approve card for ONE pending
 * medication.
 *
 * The contract this screen enforces: nothing the scan produced becomes a
 * real medication, a real DIN link, or a real reminder until the person
 * taking the pills says so. Guardrail flags are shown in plain language
 * rather than as codes, and the two BLOCKING flags (`not_on_label`,
 * `needs_schedule`) each require an explicit acknowledgement before Approve
 * unlocks -- the same gate the backend independently re-checks, so a client
 * bug cannot approve something the guards flagged.
 */
export function MedicationReviewCard({
  prescription,
  onApproved,
  onDinConfirmed,
  initialDinSuggestions,
}: MedicationReviewCardProps) {
  const { t } = useTranslation();

  const [drugName, setDrugName] = useState(prescription.drug_name);
  const [dosage, setDosage] = useState(prescription.dosage ?? '');
  const [frequency, setFrequency] = useState(prescription.frequency_type ?? 'UNKNOWN');
  const [times, setTimes] = useState<string[]>(prescription.specific_times ?? []);
  const [withFood, setWithFood] = useState(prescription.with_food);
  const [confirmed, setConfirmed] = useState<ParseFlag[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  // Open by default whenever this medication is not linked yet. Previously
  // the panel hid behind a "Link this medication to a DIN" link, so nothing
  // was ever PROPOSED -- the user had to know to go looking, and most did
  // not. A DIN is what makes a pill photo-verifiable at all (SB2 matches
  // against confirmed profile DINs and short-circuits without them), so an
  // unlinked medication silently loses a whole feature. It stays fully
  // skippable: `onCancel` collapses it back to the link.
  const [dinOpen, setDinOpen] = useState(!prescription.din_confirmed);

  const flags = prescription.parse_flags ?? [];
  const blocking = flags.filter((f) => BLOCKING_PARSE_FLAGS.includes(f));
  const suggested = SUGGESTED_TIMES[frequency] ?? [];

  const isResolved = (flag: ParseFlag) =>
    confirmed.includes(flag) || (flag === 'needs_schedule' && times.length > 0);
  const unresolved = blocking.filter((f) => !isResolved(f));
  const canApprove = unresolved.length === 0 && drugName.trim().length > 0;

  const toggleConfirmed = (flag: ParseFlag) =>
    setConfirmed((prev) => (prev.includes(flag) ? prev.filter((f) => f !== flag) : [...prev, flag]));

  const setTimeAt = (index: number, value: string) =>
    setTimes((prev) => prev.map((time, i) => (i === index ? value : time)));

  const handleApprove = async () => {
    setSaving(true);
    setError('');
    try {
      const { data } = await prescriptionsApi.update(prescription.id, {
        drug_name: drugName.trim(),
        dosage: dosage.trim() || null,
        frequency_type: frequency,
        specific_times: times,
        with_food: withFood,
        review_status: 'approved',
        confirmed_flags: confirmed,
      });
      onApproved(data);
    } catch {
      setError(t('review.saveError'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-2xl border-2 border-amber-300 bg-amber-50/60 p-4 sm:p-5 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <p className="font-bold text-slate-900 break-words min-w-0">{prescription.drug_name}</p>
        <span className="badge bg-amber-100 text-amber-800 border border-amber-300 shrink-0">
          <AlertTriangle className="h-3.5 w-3.5" /> {t('review.pendingBadge')}
        </span>
      </div>

      {/* Flag chips -- every guardrail finding, in plain language. */}
      {flags.length > 0 && (
        <ul className="flex flex-col gap-2">
          {flags.map((flag) => (
            <li
              key={flag}
              className={`rounded-lg border px-3 py-2 text-xs ${
                BLOCKING_PARSE_FLAGS.includes(flag)
                  ? 'border-amber-300 bg-amber-100/70 text-amber-900'
                  : 'border-slate-200 bg-white text-slate-600'
              }`}
            >
              <p className="font-semibold">{t(`review.flags.${flag}.title`)}</p>
              <p className="mt-0.5 leading-relaxed">{t(`review.flags.${flag}.detail`)}</p>
              {BLOCKING_PARSE_FLAGS.includes(flag) && (
                <label className="mt-2 flex items-start gap-2 font-semibold cursor-pointer min-h-[44px] sm:min-h-0 items-center">
                  <input
                    type="checkbox"
                    className="h-5 w-5 shrink-0 accent-teal-600"
                    checked={confirmed.includes(flag)}
                    onChange={() => toggleConfirmed(flag)}
                  />
                  <span>{t(`review.flags.${flag}.confirm`)}</span>
                </label>
              )}
            </li>
          ))}
        </ul>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <Input
          label={t('review.drugName')}
          id={`name-${prescription.id}`}
          value={drugName}
          onChange={(e) => setDrugName(e.target.value)}
        />
        <Input
          label={t('review.dosage')}
          id={`dosage-${prescription.id}`}
          value={dosage}
          placeholder={t('review.dosagePlaceholder')}
          onChange={(e) => setDosage(e.target.value)}
        />
      </div>

      <div>
        <label className="label" htmlFor={`freq-${prescription.id}`}>
          {t('review.frequency')}
        </label>
        <select
          id={`freq-${prescription.id}`}
          className="input-field"
          value={frequency}
          onChange={(e) => setFrequency(e.target.value)}
        >
          {FREQUENCIES.map((value) => (
            <option key={value} value={value}>
              {t(`review.freq.${value}`)}
            </option>
          ))}
        </select>
      </div>

      <div>
        <p className="label">{t('review.times')}</p>
        {times.length === 0 && <p className="text-xs text-slate-500 mb-2">{t('review.noTimes')}</p>}
        <div className="flex flex-col gap-2">
          {times.map((time, index) => (
            <div key={index} className="flex items-center gap-2">
              <Clock4 className="h-4 w-4 text-slate-400 shrink-0" />
              <input
                type="time"
                aria-label={t('review.timeAt', { n: index + 1 })}
                className="input-field !py-2 max-w-[10rem]"
                value={time}
                onChange={(e) => setTimeAt(index, e.target.value)}
              />
              <button
                type="button"
                aria-label={t('review.removeTime')}
                onClick={() => setTimes((prev) => prev.filter((_, i) => i !== index))}
                className="h-11 w-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-danger-text hover:bg-danger-bg transition-colors shrink-0"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-3 mt-2">
          <button
            type="button"
            className="text-xs font-semibold text-teal-700 underline inline-flex items-center gap-1"
            onClick={() => setTimes((prev) => [...prev, '08:00'])}
          >
            <Plus className="h-3.5 w-3.5" /> {t('review.addTime')}
          </button>
          {/* A CHOICE, never a prefilled fact -- the user taps to accept the
              canonical schedule for the frequency they selected. */}
          {suggested.length > 0 && (
            <button
              type="button"
              className="text-xs font-semibold text-teal-700 underline"
              onClick={() => setTimes(suggested)}
            >
              {t('review.useSuggested', { times: suggested.join(', ') })}
            </button>
          )}
        </div>
      </div>

      <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer min-h-[44px]">
        <input
          type="checkbox"
          className="h-5 w-5 accent-teal-600"
          checked={withFood}
          onChange={(e) => setWithFood(e.target.checked)}
        />
        {t('review.withFood')}
      </label>

      {onDinConfirmed && (
        dinOpen ? (
          <DinLinkPanel
            drugName={drugName}
            dosage={dosage || null}
            initialSuggestions={initialDinSuggestions}
            onConfirm={async (din) => {
              await onDinConfirmed(din);
              setDinOpen(false);
            }}
            onCancel={() => setDinOpen(false)}
          />
        ) : prescription.din_confirmed && prescription.din ? (
          <p className="text-xs text-success-text font-medium">
            {t('review.dinLinked', { din: prescription.din })}
          </p>
        ) : (
          <button
            type="button"
            className="text-xs font-semibold text-teal-700 underline text-left"
            onClick={() => setDinOpen(true)}
          >
            {t('review.linkDin')}
          </button>
        )
      )}

      {error && <p className="text-xs text-danger-text">{error}</p>}

      <div className="flex flex-wrap items-center gap-3">
        <Button onClick={handleApprove} loading={saving} disabled={!canApprove}>
          <CheckCircle2 className="h-4 w-4" /> {t('review.approve')}
        </Button>
        {unresolved.length > 0 && (
          <p className="text-xs text-amber-800">{t('review.approveBlocked')}</p>
        )}
      </div>

      <p className="flex items-start gap-1.5 text-[11px] text-slate-500 border-t border-amber-200 pt-2">
        <ShieldAlert className="h-3.5 w-3.5 shrink-0 mt-0.5" />
        {t('review.disclaimer')}
      </p>
    </div>
  );
}
