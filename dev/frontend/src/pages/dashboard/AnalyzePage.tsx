import { useCallback, useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Pill, FileText, Loader2, ArrowRight } from 'lucide-react';
import { CameraCapture } from '@/components/CameraCapture';
import { DisclaimerModal } from '@/components/DisclaimerModal';
import { MedicationReviewCard } from '@/components/MedicationReviewCard';
import { PillResultPanel } from '@/components/PillResultPanel';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { prescriptionsApi } from '@/api/prescriptions';
import { pillApi } from '@/api/pill';
import { voice } from '@/lib/voiceAssistant';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import type { Prescription, PrescriptionWithSuggestions, PillAnalysisV2Response } from '@/types';

type Mode = 'prescription' | 'pill';
type Stage = 'capture' | 'uploading' | 'done' | 'error';

interface ApiErrorInfo {
  status?: number;
  code?: string;
  message?: string;
}

function extractApiError(err: unknown): ApiErrorInfo {
  const response = (
    err as { response?: { status?: number; data?: { detail?: { error?: { code?: string; message?: string } } } } }
  )?.response;
  return {
    status: response?.status,
    code: response?.data?.detail?.error?.code,
    message: response?.data?.detail?.error?.message,
  };
}

export default function AnalyzePage() {
  const { t } = useTranslation();

  // Mode is forced by the route (Phase 6 -- the in-page switcher is gone;
  // `/dashboard/scan-prescription` and `/dashboard/scan-pill` both render
  // this component, `/dashboard/analyze` redirects to scan-pill). See
  // router/index.tsx.
  const { pathname } = useLocation();
  const mode: Mode = pathname.includes('scan-prescription') ? 'prescription' : 'pill';
  useVoicePageAnnounce(t(mode === 'prescription' ? 'nav.scanRx' : 'nav.scanPill'));

  const navigate = useNavigate();
  const [stage, setStage] = useState<Stage>('capture');
  const [errorMsg, setErrorMsg] = useState('');
  const [showResultDisclaimer, setShowResultDisclaimer] = useState(false);
  const [prescriptionResults, setPrescriptionResults] = useState<PrescriptionWithSuggestions[] | null>(null);
  /** Server rows for the just-scanned medications, keyed by id, updated in
   * place as the user confirms a DIN or approves. The create response is the
   * seed; every later PATCH response replaces its entry, so the review cards
   * always render what the SERVER says rather than optimistic local state. */
  const [reviewRows, setReviewRows] = useState<Record<string, Prescription>>({});
  const [pillResult, setPillResult] = useState<PillAnalysisV2Response | null>(null);
  const [pillProgressStep, setPillProgressStep] = useState(0);

  // Staged copy shown while a pill scan is in flight -- the first sidecar
  // call per process is slow (model load + a fresh Paddle OCR subprocess
  // spawn), commonly 30s+, so a single static spinner reads as broken.
  const pillProgressMessages = t('analyze.pillProgress', { returnObjects: true }) as string[];

  // FixbySonnet1 Task 4b: sidecar-down (503 OCR_UNAVAILABLE/BRAINS_UNAVAILABLE),
  // backend crash (500), and a genuine unreadable-photo outcome must read
  // differently -- previously all three rendered the same generic
  // "retake the photo" text, which was actively misleading when the photo
  // was fine and the sidecar was simply unreachable.
  const resolveErrorMessage = useCallback((err: unknown, fallbackKey: string): string => {
    const { status, code, message } = extractApiError(err);
    if (status === 503 || code === 'OCR_UNAVAILABLE' || code === 'BRAINS_UNAVAILABLE') {
      return t('analyze.errorOcrUnavailable');
    }
    if (status !== undefined && status >= 500) {
      return t('analyze.errorServerGeneric');
    }
    // Genuine no-text/bad-photo outcome (4xx, or no response at all) --
    // keep the existing retake-in-good-lighting guidance, still preferring
    // the backend's own message when it provided one.
    return message ?? t(fallbackKey);
  }, [t]);

  const reset = useCallback(() => {
    setStage('capture');
    setErrorMsg('');
    setPrescriptionResults(null);
    setReviewRows({});
    setPillResult(null);
  }, []);

  // Route changed under us (e.g. the "scanning a pill instead?" cross-link,
  // or the PillResultPanel "no confirmed medications" CTA navigating to
  // scan-prescription) -- clear any in-flight/previous-mode state.
  useEffect(() => {
    reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  // Staged progress copy while a pill scan is in flight (first call per
  // sidecar process is commonly 30s+ -- a single static spinner reads as
  // broken without this).
  useEffect(() => {
    if (stage !== 'uploading' || mode !== 'pill') {
      setPillProgressStep(0);
      return;
    }
    const id = window.setInterval(() => {
      setPillProgressStep((s) => Math.min(s + 1, pillProgressMessages.length - 1));
    }, 6000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stage, mode]);

  const handlePrescriptionCapture = async (blob: Blob) => {
    setStage('uploading');
    try {
      const { data } = await prescriptionsApi.upload(blob);
      setPrescriptionResults(data);
      setReviewRows(Object.fromEntries(data.map((p) => [p.id, p as Prescription])));
      setStage('done');
      setShowResultDisclaimer(true);
      // "read", not "saved": nothing is on the schedule until it is approved.
      voice.speak(
        data.length === 1
          ? `${data[0].drug_name} detected. Please review it before it is added to your schedule.`
          : `${data.length} medications detected: ${data.map((p) => p.drug_name).join(', ')}. Please review each one before it is added to your schedule.`,
      );
    } catch (err: unknown) {
      setErrorMsg(resolveErrorMessage(err, 'analyze.errorPrescriptionDefault'));
      setStage('error');
    }
  };

  const confirmDin = async (prescriptionId: string, din: string) => {
    const { data } = await prescriptionsApi.update(prescriptionId, { din });
    setReviewRows((prev) => ({ ...prev, [prescriptionId]: data }));
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
      setErrorMsg(resolveErrorMessage(err, 'analyze.errorPillDefault'));
      setStage('error');
    }
  };

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          {mode === 'prescription' ? <FileText className="h-6 w-6 text-teal-600" /> : <Pill className="h-6 w-6 text-teal-600" />}
          {t(mode === 'prescription' ? 'nav.scanRx' : 'nav.scanPill')}
        </h1>
        {stage === 'capture' && (
          <Link
            to={mode === 'prescription' ? '/dashboard/scan-pill' : '/dashboard/scan-prescription'}
            className="text-sm font-semibold text-teal-700 underline"
          >
            {t(mode === 'prescription' ? 'analyze.crossLinkToPill' : 'analyze.crossLinkToRx')}
          </Link>
        )}
      </div>

      {stage === 'capture' && (
        <Card padding="none" className="p-0 sm:p-6 rounded-none sm:rounded-2xl border-x-0 sm:border-x -mx-4 sm:mx-0">
          <CameraCapture
            captureLabel={t(mode === 'prescription' ? 'analyze.captureRxLabel' : 'analyze.capturePillLabel')}
            // FixbySonnet1 Task 8: forced illumination is pill-imprint-scoped
            // evidence (NB08) -- Rx-scan (a flat printed document) never
            // forces the torch.
            forceFlash={mode === 'pill'}
            onConfirm={(blob) => (mode === 'prescription' ? handlePrescriptionCapture(blob) : handlePillCapture(blob))}
          />
        </Card>
      )}

      {stage === 'uploading' && (
        <Card>
          <div className="flex flex-col items-center justify-center gap-3 py-12" role="status" aria-live="polite">
            <Loader2 className="h-10 w-10 text-teal-600 animate-spin" />
            <p className="text-slate-900 font-semibold text-center">
              {mode === 'prescription' ? t('analyze.uploadingRx') : pillProgressMessages[pillProgressStep]}
            </p>
            <p className="text-slate-500 text-sm">
              {mode === 'prescription' ? t('analyze.uploadingRxSub') : t('analyze.pillProgressSub')}
            </p>
          </div>
        </Card>
      )}

      {stage === 'error' && (
        <div className="space-y-4">
          <Alert variant="error" message={errorMsg} />
          <Button onClick={reset}>{t('analyze.tryAgain')}</Button>
        </div>
      )}

      {stage === 'done' && (
        <DisclaimerModal open={showResultDisclaimer} onAccept={() => setShowResultDisclaimer(false)} />
      )}

      {stage === 'done' && !showResultDisclaimer && prescriptionResults && prescriptionResults.length > 0 && (
        <div className="space-y-5 animate-slide-up">
          {/* Deliberately NOT a green "saved" card. Nothing has been added to
              the user's schedule yet -- these are proposals awaiting review
              (FixbyOPUS3 §0.1), and success-green for a pending proposal
              would be the app telling a comfortable lie. */}
          <div>
            <h2 className="text-lg font-bold text-slate-900">{t('review.title')}</h2>
            <p className="text-sm text-slate-600 mt-1">{t('review.subtitle')}</p>
          </div>

          <div className="space-y-4">
            {prescriptionResults.map((p) => (
              <MedicationReviewCard
                key={p.id}
                prescription={reviewRows[p.id] ?? p}
                initialDinSuggestions={p.din_suggestions}
                onApproved={(updated) => setReviewRows((prev) => ({ ...prev, [p.id]: updated }))}
                onDinConfirmed={(din) => confirmDin(p.id, din)}
              />
            ))}
          </div>

          <div className="flex gap-3">
            <Button variant="secondary" onClick={reset}>{t('pillResult.scanAnother')}</Button>
            <Button onClick={() => navigate('/dashboard/medications')}>
              {t('analyze.viewMyMedications')} <ArrowRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {stage === 'done' && !showResultDisclaimer && pillResult && (
        <PillResultPanel
          result={pillResult}
          onRetake={reset}
          onGoToPrescriptions={() => navigate('/dashboard/scan-prescription')}
        />
      )}
    </div>
  );
}
