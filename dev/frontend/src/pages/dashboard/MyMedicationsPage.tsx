import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Pill, ScanLine, Trash2, Clock4, ImageIcon, MessageCircleQuestion, CameraOff } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import ReminderAudio from '@/components/ReminderAudio';
import PrescriptionImageModal from '@/components/PrescriptionImageModal';
import InstructionsPanel from '@/components/InstructionsPanel';
import { DinLinkPanel } from '@/components/DinLinkPanel';
import { MedicationReviewCard } from '@/components/MedicationReviewCard';
import { prescriptionsApi } from '@/api/prescriptions';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import { voice } from '@/lib/voiceAssistant';
import { useAuthStore } from '@/store/authStore';
import type { Prescription } from '@/types';

const SLOT_BADGE: Record<string, string> = {
  morning: 'slot-badge-morning',
  afternoon: 'slot-badge-afternoon',
  evening: 'slot-badge-evening',
  night: 'slot-badge-night',
};

export default function MyMedicationsPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('meds.title'));
  const firstName = useAuthStore((s) => s.user?.first_name) || 'there';
  const [prescriptions, setPrescriptions] = useState<Prescription[] | null>(null);
  const [error, setError] = useState('');
  const [viewingImageId, setViewingImageId] = useState<string | null>(null);
  const [dinEditingId, setDinEditingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const { data } = await prescriptionsApi.listMine();
      setPrescriptions(data);
      voice.speak(
        data.length === 1 ? t('meds.announceOne') : t('meds.announceMany', { count: data.length }),
      );
    } catch {
      setError(t('meds.loadError'));
    }
  }, [t]);

  // Pending medications are PROPOSALS from a scan -- they carry no reminders
  // and are not part of the medication list until the user approves them, so
  // they render in their own amber review panel above the real list rather
  // than mixed in with it (FixbyOPUS3 Task A4).
  const pending = prescriptions?.filter((p) => p.review_status === 'pending') ?? [];
  const approved = prescriptions?.filter((p) => p.review_status !== 'pending') ?? [];

  const handleApproved = (updated: Prescription) =>
    setPrescriptions((prev) => prev?.map((p) => (p.id === updated.id ? updated : p)) ?? null);

  useEffect(() => {
    load();
  }, [load]);

  const handleRemove = async (id: string) => {
    if (!window.confirm(t('meds.removeConfirm'))) return;
    await prescriptionsApi.remove(id);
    setPrescriptions((prev) => prev?.filter((p) => p.id !== id) ?? null);
  };

  const handleConfirmDin = async (id: string, din: string) => {
    const { data } = await prescriptionsApi.update(id, { din });
    // Take the server's row wholesale rather than cherry-picking fields. The
    // earlier version merged only `din` and `din_confirmed`, which silently
    // dropped `pill_verifiable` -- resolved by the backend during this very
    // call -- so the "can't be checked by photo" badge did not appear until
    // the next page load. That is the one moment it matters most: the person
    // who just linked an insulin DIN is exactly who needs telling. Spreading
    // the response also stops the next field added to PrescriptionOut from
    // reintroducing the same class of bug.
    setPrescriptions((prev) => prev?.map((p) => (p.id === id ? { ...p, ...data } : p)) ?? null);
    setDinEditingId(null);
  };

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-slate-900">{t('meds.title')}</h1>
        <Link to="/dashboard/scan-prescription">
          <Button>
            <ScanLine className="h-4 w-4" /> {t('meds.add')}
          </Button>
        </Link>
      </div>

      {error && <Alert variant="error" message={error} />}

      {pending.length > 0 && (
        <section className="space-y-4" aria-labelledby="review-heading">
          <div>
            <h2 id="review-heading" className="text-lg font-bold text-slate-900">
              {t('review.title')}
            </h2>
            <p className="text-sm text-slate-600 mt-1">{t('review.subtitle')}</p>
          </div>
          {pending.map((p) => (
            <MedicationReviewCard
              key={p.id}
              prescription={p}
              onApproved={handleApproved}
              onDinConfirmed={(din) => handleConfirmDin(p.id, din)}
            />
          ))}
        </section>
      )}

      {prescriptions && prescriptions.length === 0 && (
        <Card className="text-center py-14">
          <div className="h-16 w-16 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
            <Pill className="h-8 w-8 text-teal-600" />
          </div>
          <p className="font-semibold text-slate-900">{t('meds.emptyTitle')}</p>
          <p className="text-sm text-slate-500 mt-1.5 max-w-sm mx-auto">{t('meds.emptyBody')}</p>
          <Link to="/dashboard/scan-prescription" className="inline-block mt-5">
            <Button size="lg">
              <ScanLine className="h-4 w-4" /> {t('meds.emptyCta')}
            </Button>
          </Link>
        </Card>
      )}

      {approved.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {approved.map((p) => (
            <Card key={p.id} className="space-y-3">
              <div className="flex items-start justify-between">
                <div>
                  <p className="font-bold text-slate-900 text-lg">{p.drug_name}</p>
                  {p.dosage && <p className="text-base text-slate-600 mt-0.5">{p.dosage}</p>}
                </div>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label={t('meds.viewOriginal', { name: p.drug_name })}
                    onClick={() => setViewingImageId(p.id)}
                    className="h-11 w-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-teal-600 hover:bg-teal-50 transition-colors"
                  >
                    <ImageIcon className="h-4 w-4" />
                  </button>
                  <button
                    type="button"
                    aria-label={t('meds.remove', { name: p.drug_name })}
                    onClick={() => handleRemove(p.id)}
                    className="h-11 w-11 rounded-xl flex items-center justify-center text-slate-400 hover:text-danger-text hover:bg-danger-bg transition-colors"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                {p.frequency_type === 'PRN' ? (
                  <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                    {t('meds.asNeeded')}
                    {p.max_daily_dose ? ` · ${t('meds.maxPerDay', { dose: p.max_daily_dose })}` : ''}
                  </span>
                ) : (
                  p.time_slots.map((slot) => (
                    <span key={slot} className={`badge ${SLOT_BADGE[slot] ?? ''}`}>
                      {/* Unknown slots fall back to the raw value rather than
                          rendering a bare i18n key at the user. */}
                      {t(`meds.slots.${slot}`, { defaultValue: slot })}
                    </span>
                  ))
                )}
              </div>

              {p.specific_times.length > 0 && (
                <p className="flex items-center gap-1.5 text-sm text-slate-500">
                  <Clock4 className="h-3.5 w-3.5" />
                  {p.specific_times.join(', ')}
                </p>
              )}

              <ReminderAudio medicationName={p.drug_name} patientFirstName={firstName} />
              <InstructionsPanel prescription={p} />

              {p.din_confirmed && p.din && (
                <Link
                  to={`/dashboard/qa?din=${encodeURIComponent(p.din)}&name=${encodeURIComponent(p.drug_name)}`}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-700 underline w-fit"
                >
                  <MessageCircleQuestion className="h-3.5 w-3.5" /> {t('meds.askAbout')}
                </Link>
              )}

              {dinEditingId === p.id ? (
                <DinLinkPanel
                  drugName={p.drug_name}
                  dosage={p.dosage}
                  onConfirm={(din) => handleConfirmDin(p.id, din)}
                  onCancel={() => setDinEditingId(null)}
                />
              ) : p.din_confirmed && p.din ? (
                <>
                  <div className="flex items-center justify-between gap-3 rounded-lg border border-success-border bg-success-bg px-3 py-2">
                    <p className="text-xs text-success-text font-medium">
                      {t('meds.linkedToDin', { din: p.din })}
                    </p>
                    <button
                      type="button"
                      className="text-xs font-semibold text-teal-700 underline shrink-0"
                      onClick={() => setDinEditingId(p.id)}
                    >
                      {t('meds.change')}
                    </button>
                  </div>
                  {/* Task B3. Rendered ONLY on an explicit `false` -- `null`
                      means we could not establish it, and an unfounded
                      "can't be checked by photo" would teach a user not to
                      verify a pill they actually could verify. */}
                  {p.pill_verifiable === false && (
                    <p className="flex items-start gap-1.5 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-600">
                      <CameraOff className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                      {t('review.notPillVerifiable')}
                    </p>
                  )}
                </>
              ) : (
                <button
                  type="button"
                  className="text-xs font-semibold text-teal-700 underline text-left"
                  onClick={() => setDinEditingId(p.id)}
                >
                  {t('meds.linkToDin')}
                </button>
              )}
            </Card>
          ))}
        </div>
      )}

      {viewingImageId && (
        <PrescriptionImageModal prescriptionId={viewingImageId} onClose={() => setViewingImageId(null)} />
      )}
    </div>
  );
}
