import { useCallback, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Grid3x3, Loader2, RefreshCw } from 'lucide-react';
import { CameraCapture } from '@/components/CameraCapture';
import { TraySlotGrid } from '@/components/tray/TraySlotGrid';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { trayApi } from '@/api/tray';
import { resolveTrayMsg } from '@/lib/trayMessages';
import { needsReshoot, noneRouteForAttempt, resolveTrayApiError, type TrayAttempt } from '@/lib/trayPageLogic';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import type { TrayAnalysisResponse } from '@/types';

type Stage = 'capture' | 'uploading' | 'reshoot' | 'done' | 'error';

/** Localhost tray-check page (MPR1-T07): one photo of all six wells, six
 * per-slot verdicts, the pharmacist hedge, and Muthu's D-4 terminal-after-1-
 * reshoot state machine. `runAnalyze` is the ENTIRE state machine -- attempt
 * 1 always calls with `none_route="retry"`; if (and only if) that response
 * still has a non-terminal occupied slot, the page offers exactly one
 * reshoot (attempt 2, `none_route="terminal"`) and is done regardless of
 * what attempt 2 comes back with. A brand new upload after a completed
 * session (`reset`) is the only thing that starts the count back at 1. */
export default function TrayCheckPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('nav.trayCheck'));
  const navigate = useNavigate();

  const [stage, setStage] = useState<Stage>('capture');
  // Only `setAttempt` is read here -- `runAnalyze` is always called with the
  // attempt it should run AS AN ARGUMENT (never inferred from state, so a
  // stale closure can't run the wrong `none_route`); the state value exists
  // so a re-render (e.g. after Try Again) can still recover it if needed.
  const [, setAttempt] = useState<TrayAttempt>(1);
  const [result, setResult] = useState<TrayAnalysisResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState('');

  const reset = useCallback(() => {
    setStage('capture');
    setAttempt(1);
    setResult(null);
    setErrorMsg('');
  }, []);

  const runAnalyze = useCallback(
    async (blob: Blob, thisAttempt: TrayAttempt) => {
      setStage('uploading');
      setAttempt(thisAttempt);
      try {
        const { data } = await trayApi.analyze(blob, noneRouteForAttempt(thisAttempt));
        setResult(data);
        setStage(thisAttempt === 1 && needsReshoot(data.slots) ? 'reshoot' : 'done');
      } catch (err: unknown) {
        setErrorMsg(resolveTrayApiError(err, t));
        setStage('error');
      }
    },
    [t],
  );

  const profileNotice = result ? resolveTrayMsg(result.profile.notice) : null;
  const topMessage = result ? resolveTrayMsg(result.message) : null;

  return (
    <div className="space-y-6 page-enter max-w-5xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
        <Grid3x3 className="h-6 w-6 text-teal-600" />
        {t('nav.trayCheck')}
      </h1>

      {stage === 'capture' && (
        <Card padding="none" className="p-0 sm:p-6 rounded-none sm:rounded-2xl border-x-0 sm:border-x -mx-4 sm:mx-0 space-y-4">
          <p className="text-sm text-slate-600 px-4 pt-4 sm:px-0 sm:pt-0">{t('trayCheck.intro')}</p>
          <CameraCapture
            captureLabel={t('trayCheck.captureLabel')}
            forceFlash
            onConfirm={(blob) => runAnalyze(blob, 1)}
          />
        </Card>
      )}

      {stage === 'uploading' && (
        <Card>
          <div className="flex flex-col items-center justify-center gap-3 py-12" role="status" aria-live="polite">
            <Loader2 className="h-10 w-10 text-teal-600 animate-spin" />
            <p className="text-slate-900 font-semibold text-center">{t('trayCheck.uploading')}</p>
            <p className="text-slate-500 text-sm">{t('trayCheck.uploadingSub')}</p>
          </div>
        </Card>
      )}

      {stage === 'error' && (
        <div className="space-y-4">
          <Alert variant="error" message={errorMsg} />
          <Button onClick={reset}>{t('trayCheck.tryAgain')}</Button>
        </div>
      )}

      {(stage === 'reshoot' || stage === 'done') && result && (
        <div className="space-y-4 animate-slide-up">
          {topMessage && <Alert variant="info" message={topMessage} />}
          {profileNotice && <Alert variant="warning" message={profileNotice} />}

          <TraySlotGrid slots={result.slots} />

          {stage === 'reshoot' && (
            <Card className="space-y-4 border-warning-border bg-warning-bg">
              <div>
                <p className="font-semibold text-slate-900">{t('trayCheck.reshootTitle')}</p>
                <p className="text-sm text-slate-700 mt-1">{t('trayCheck.reshootBody')}</p>
              </div>
              <CameraCapture
                captureLabel={t('trayCheck.reshootCaptureLabel')}
                forceFlash
                onConfirm={(blob) => runAnalyze(blob, 2)}
              />
            </Card>
          )}

          {stage === 'done' && (
            <div className="flex gap-3">
              <Button variant="secondary" onClick={reset}>
                <RefreshCw className="h-4 w-4" /> {t('trayCheck.scanNewTray')}
              </Button>
              {result.status === 'no_profile' && (
                <Button onClick={() => navigate('/dashboard/scan-prescription')}>
                  {t('pillResult.noProfile.cta')}
                </Button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
