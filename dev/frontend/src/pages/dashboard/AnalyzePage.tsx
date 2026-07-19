import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Pill, FileText, Loader2, CheckCircle2, ArrowRight } from 'lucide-react';
import { CameraCapture } from '@/components/CameraCapture';
import { DisclaimerModal } from '@/components/DisclaimerModal';
import { DinLinkPanel } from '@/components/DinLinkPanel';
import { PillResultPanel } from '@/components/PillResultPanel';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { prescriptionsApi } from '@/api/prescriptions';
import { pillApi } from '@/api/pill';
import { voice } from '@/lib/voiceAssistant';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import type { PrescriptionWithSuggestions, PillAnalysisV2Response } from '@/types';

/** Staged copy shown while a pill scan is in flight -- the first sidecar
 * call per process is slow (model load + a fresh Paddle OCR subprocess
 * spawn), commonly 30s+, so a single static spinner reads as broken. */
const PILL_PROGRESS_MESSAGES = [
  'Analyzing photo… this can take up to a minute.',
  'Reading colour, shape, and imprint…',
  'Comparing against your medications…',
  'Still working — almost there…',
];

/** Per-prescription DIN-link UI state, tracked client-side after a scan so
 * the confirm step can be shown/dismissed without another round trip. */
interface DinLinkState {
  din: string | null;
  confirmed: boolean;
  open: boolean;
}

type Mode = 'prescription' | 'pill';
type Stage = 'capture' | 'uploading' | 'done' | 'error';

const SLOT_BADGE: Record<string, string> = {
  morning: 'slot-badge-morning',
  afternoon: 'slot-badge-afternoon',
  evening: 'slot-badge-evening',
  night: 'slot-badge-night',
};

export default function AnalyzePage() {
  useVoicePageAnnounce('Analyze Medication');

  const navigate = useNavigate();
  const [mode, setMode] = useState<Mode>('prescription');
  const [stage, setStage] = useState<Stage>('capture');
  const [errorMsg, setErrorMsg] = useState('');
  const [showResultDisclaimer, setShowResultDisclaimer] = useState(false);
  const [prescriptionResults, setPrescriptionResults] = useState<PrescriptionWithSuggestions[] | null>(null);
  const [dinLinks, setDinLinks] = useState<Record<string, DinLinkState>>({});
  const [pillResult, setPillResult] = useState<PillAnalysisV2Response | null>(null);
  const [pillProgressStep, setPillProgressStep] = useState(0);

  const reset = useCallback(() => {
    setStage('capture');
    setErrorMsg('');
    setPrescriptionResults(null);
    setDinLinks({});
    setPillResult(null);
  }, []);

  const switchMode = (next: Mode) => {
    setMode(next);
    reset();
  };

  // Staged progress copy while a pill scan is in flight (first call per
  // sidecar process is commonly 30s+ -- a single static spinner reads as
  // broken without this).
  useEffect(() => {
    if (stage !== 'uploading' || mode !== 'pill') {
      setPillProgressStep(0);
      return;
    }
    const id = window.setInterval(() => {
      setPillProgressStep((s) => Math.min(s + 1, PILL_PROGRESS_MESSAGES.length - 1));
    }, 6000);
    return () => window.clearInterval(id);
  }, [stage, mode]);

  const handlePrescriptionCapture = async (blob: Blob) => {
    setStage('uploading');
    try {
      const { data } = await prescriptionsApi.upload(blob);
      setPrescriptionResults(data);
      setDinLinks(
        Object.fromEntries(
          data.map((p) => [
            p.id,
            { din: p.din, confirmed: p.din_confirmed, open: !p.din_confirmed } satisfies DinLinkState,
          ]),
        ),
      );
      setStage('done');
      setShowResultDisclaimer(true);
      voice.speak(
        data.length === 1
          ? `${data[0].drug_name} detected. Saved to your medications.`
          : `${data.length} medications detected: ${data.map((p) => p.drug_name).join(', ')}. Saved to your medications.`,
      );
    } catch (err: unknown) {
      const message = (err as { response?: { data?: { detail?: { error?: { message?: string } } } } })
        ?.response?.data?.detail?.error?.message;
      setErrorMsg(message ?? 'Could not read that prescription label. Please retake the photo in good lighting.');
      setStage('error');
    }
  };

  const confirmDin = async (prescriptionId: string, din: string) => {
    const { data } = await prescriptionsApi.update(prescriptionId, { din });
    setDinLinks((prev) => ({
      ...prev,
      [prescriptionId]: { din: data.din, confirmed: data.din_confirmed, open: false },
    }));
  };

  const skipDin = (prescriptionId: string) => {
    setDinLinks((prev) => ({ ...prev, [prescriptionId]: { ...prev[prescriptionId], open: false } }));
  };

  const reopenDin = (prescriptionId: string) => {
    setDinLinks((prev) => ({ ...prev, [prescriptionId]: { ...prev[prescriptionId], open: true } }));
  };

  const handlePillCapture = async (blob: Blob) => {
    setStage('uploading');
    try {
      const { data } = await pillApi.analyze(blob);
      setPillResult(data);
      setStage('done');
      setShowResultDisclaimer(true);

      if (data.status === 'no_profile') {
        voice.speak('You have no confirmed medications yet. Scan a prescription first.');
      } else if (data.record && !data.record.detected) {
        voice.speak("Couldn't find a pill in that photo. Please try again.");
      } else if (data.match?.decision === 'verify') {
        const top = data.match.ranked_candidates[0];
        voice.speak(`This matches ${top?.product ?? 'your medication'}.`);
      } else if (data.match?.decision === 'reject') {
        voice.speak('Warning. This pill does not match any medication in your profile.');
      } else if (data.match?.decision === 'abstain' && data.match.abstain_action === 'ask_to_flip') {
        voice.speak('Please turn the pill over and photograph the other side.');
      } else if (data.match?.decision === 'abstain') {
        voice.speak("We're not fully certain. Please check the shortlist.");
      }
    } catch (err: unknown) {
      const code = (err as { response?: { data?: { detail?: { error?: { code?: string; message?: string } } } } })
        ?.response?.data?.detail?.error;
      setErrorMsg(code?.message ?? 'Could not analyze that pill. Try a plain, well-lit background.');
      setStage('error');
    }
  };

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <div className="flex gap-2" role="tablist" aria-label="Scan mode">
        <button
          role="tab"
          aria-selected={mode === 'prescription'}
          onClick={() => switchMode('prescription')}
          className={`flex-1 min-h-[44px] flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition-colors ${
            mode === 'prescription' ? 'bg-primary text-white border-primary' : 'bg-white text-slate-600 border-slate-200 hover:border-teal-300'
          }`}
        >
          <FileText className="h-4 w-4" /> Scan Prescription
        </button>
        <button
          role="tab"
          aria-selected={mode === 'pill'}
          onClick={() => switchMode('pill')}
          className={`flex-1 min-h-[44px] flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-sm font-semibold transition-colors ${
            mode === 'pill' ? 'bg-primary text-white border-primary' : 'bg-white text-slate-600 border-slate-200 hover:border-teal-300'
          }`}
        >
          <Pill className="h-4 w-4" /> Scan Pill
        </button>
      </div>

      {stage === 'capture' && (
        <Card>
          <CameraCapture
            captureLabel={mode === 'prescription' ? 'Capture prescription label' : 'Capture pill photo'}
            onConfirm={(blob) => (mode === 'prescription' ? handlePrescriptionCapture(blob) : handlePillCapture(blob))}
          />
        </Card>
      )}

      {stage === 'uploading' && (
        <Card>
          <div className="flex flex-col items-center justify-center gap-3 py-12" role="status" aria-live="polite">
            <Loader2 className="h-10 w-10 text-teal-600 animate-spin" />
            <p className="text-slate-900 font-semibold text-center">
              {mode === 'prescription' ? 'Reading your prescription label…' : PILL_PROGRESS_MESSAGES[pillProgressStep]}
            </p>
            <p className="text-slate-500 text-sm">
              {mode === 'prescription' ? 'This usually takes a few seconds.' : 'The first scan can take up to a minute.'}
            </p>
          </div>
        </Card>
      )}

      {stage === 'error' && (
        <div className="space-y-4">
          <Alert variant="error" message={errorMsg} />
          <Button onClick={reset}>Try Again</Button>
        </div>
      )}

      {stage === 'done' && (
        <DisclaimerModal open={showResultDisclaimer} onAccept={() => setShowResultDisclaimer(false)} />
      )}

      {stage === 'done' && !showResultDisclaimer && prescriptionResults && prescriptionResults.length > 0 && (
        <div className="space-y-5 animate-slide-up">
          <Card className="border-success-border bg-success-bg">
            <div className="flex items-start gap-3">
              <CheckCircle2 className="h-6 w-6 text-success-text shrink-0" />
              <div className="flex-1">
                <p className="font-semibold text-slate-900">
                  {prescriptionResults.length === 1
                    ? 'Prescription saved'
                    : `${prescriptionResults.length} medications saved`}
                </p>
                <div className="space-y-3 mt-3">
                  {prescriptionResults.map((p) => (
                    <div key={p.id} className="border-t border-success-border/50 pt-3 first:border-t-0 first:pt-0">
                      <p className="text-sm text-slate-700">
                        <strong>{p.drug_name}</strong>
                        {p.dosage ? ` · ${p.dosage}` : ''}
                      </p>
                      <div className="flex flex-wrap gap-2 mt-2">
                        {p.frequency_type === 'PRN' ? (
                          <span className="badge bg-amber-50 text-amber-700 border border-amber-200">
                            As needed{p.max_daily_dose ? ` · max ${p.max_daily_dose}/24h` : ''}
                          </span>
                        ) : (
                          p.time_slots.map((slot) => (
                            <span key={slot} className={`badge ${SLOT_BADGE[slot] ?? ''}`}>
                              {slot.charAt(0).toUpperCase() + slot.slice(1)}
                            </span>
                          ))
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </Card>

          <div className="space-y-3">
            {prescriptionResults.map((p) => {
              const link = dinLinks[p.id];
              if (!link) return null;
              if (link.open) {
                return (
                  <div key={p.id}>
                    <p className="text-xs font-semibold text-slate-500 mb-1.5">{p.drug_name}</p>
                    <DinLinkPanel
                      drugName={p.drug_name}
                      dosage={p.dosage}
                      initialSuggestions={p.din_suggestions}
                      onConfirm={(din) => confirmDin(p.id, din)}
                      onSkip={() => skipDin(p.id)}
                    />
                  </div>
                );
              }
              return (
                <div
                  key={p.id}
                  className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
                >
                  <p className="text-xs text-slate-600">
                    <strong>{p.drug_name}</strong>{' '}
                    {link.confirmed && link.din ? (
                      <span className="text-success-text">Linked to DIN {link.din}</span>
                    ) : (
                      <span className="text-slate-400">Not linked to a DIN yet</span>
                    )}
                  </p>
                  <button
                    type="button"
                    className="text-xs font-semibold text-teal-700 underline shrink-0"
                    onClick={() => reopenDin(p.id)}
                  >
                    {link.confirmed ? 'Change' : 'Link DIN'}
                  </button>
                </div>
              );
            })}
          </div>

          <div className="flex gap-3">
            <Button variant="secondary" onClick={reset}>Scan Another</Button>
            <Button onClick={() => navigate('/dashboard/medications')}>
              View My Medications <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {stage === 'done' && !showResultDisclaimer && pillResult && (
        <PillResultPanel
          result={pillResult}
          onRetake={reset}
          onGoToPrescriptions={() => switchMode('prescription')}
        />
      )}
    </div>
  );
}
