import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Cpu, HardDrive, Play, Power, Square, Zap, ZapOff } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { adminApi, type SidecarProfile, type SidecarSupervisorStatus } from '@/api/admin';
import { extractApiErrorMessage } from '@/lib/apiError';

const STATUS_POLL_MS = 10_000;

/** Same on/off pill switch as `SettingsPage.tsx`'s local `Toggle` -- kept as
 * its own copy here (not extracted to `ui/`) so this page's diff stays
 * self-contained, same as that page's own local definition. */
function Toggle({ checked, onChange, label, disabled }: { checked: boolean; onChange: (v: boolean) => void; label: string; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-7 w-12 min-h-[28px] items-center rounded-full transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
        checked ? 'bg-primary' : 'bg-slate-300'
      }`}
    >
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

export default function AdminSidecarPage() {
  const { t } = useTranslation();

  const [status, setStatus] = useState<SidecarSupervisorStatus | null>(null);
  const [statusError, setStatusError] = useState('');
  const [loadingStatus, setLoadingStatus] = useState(true);

  const [profile, setProfile] = useState<SidecarProfile>('dev');
  const [warm, setWarm] = useState(true);
  const [force, setForce] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionNote, setActionNote] = useState('');
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);

  // Guards a poll landing after the component (or the admin nav-away) has
  // already unmounted -- same pattern as SidecarTicker.
  const mounted = useRef(true);

  const refreshStatus = useCallback(() => {
    adminApi
      .getSidecarStatus()
      .then(({ data }) => {
        if (!mounted.current) return;
        setStatus(data);
        setStatusError('');
      })
      .catch((err) => {
        if (!mounted.current) return;
        setStatusError(extractApiErrorMessage(err, t('admin.sidecarActionError')));
      })
      .finally(() => {
        if (mounted.current) setLoadingStatus(false);
      });
  }, [t]);

  useEffect(() => {
    mounted.current = true;
    refreshStatus();
    const id = window.setInterval(refreshStatus, STATUS_POLL_MS);
    return () => {
      mounted.current = false;
      window.clearInterval(id);
    };
  }, [refreshStatus]);

  const handleStart = async () => {
    setActionError('');
    setActionNote('');
    setStarting(true);
    try {
      const { data } = await adminApi.startSidecar({ profile, warm, force });
      setActionNote(t('admin.startSuccess', { pid: data.pid, profile: data.profile }));
      refreshStatus();
    } catch (err) {
      // The 422 guard-refused text (low RAM / on-battery) is a safety
      // message, not a generic failure -- it must reach the admin verbatim,
      // never collapsed into a fallback string.
      setActionError(extractApiErrorMessage(err, t('admin.sidecarActionError')));
    } finally {
      setStarting(false);
    }
  };

  const handleStop = async () => {
    if (!window.confirm(t('admin.confirmStop'))) return;
    setActionError('');
    setActionNote('');
    setStopping(true);
    try {
      await adminApi.stopSidecar();
      setActionNote(t('admin.stopSuccess'));
      refreshStatus();
    } catch (err) {
      setActionError(extractApiErrorMessage(err, t('admin.sidecarActionError')));
    } finally {
      setStopping(false);
    }
  };

  return (
    <div className="space-y-6 page-enter max-w-3xl mx-auto">
      <div>
        <h1 className="text-xl font-bold text-slate-900">{t('admin.sidecarControl')}</h1>
        <p className="text-sm text-slate-500 mt-1">{t('admin.sidecarSubtitle')}</p>
      </div>

      {statusError && <Alert variant="error" message={statusError} />}

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-900 text-sm">{t('admin.sidecarStatusTitle')}</h2>
          {status && (
            <span
              className={`badge ${
                status.sidecar_running
                  ? 'bg-success-bg text-success-text border border-success-border'
                  : 'bg-warning-bg text-warning-text border border-warning-border'
              }`}
            >
              {status.sidecar_running ? t('admin.running') : t('admin.stopped')}
            </span>
          )}
        </div>

        {loadingStatus ? (
          <div className="flex items-center justify-center py-8">
            <div className="h-6 w-6 rounded-full border-2 border-teal-600 border-t-transparent animate-spin" />
          </div>
        ) : status ? (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {status.sidecar_health && (
              <div className="col-span-2 sm:col-span-4">
                <p className="text-xs text-slate-500 font-medium">{t('admin.componentHealth')}</p>
                {typeof status.sidecar_health === 'string' ? (
                  <p className="text-sm text-slate-900 mt-0.5">{status.sidecar_health}</p>
                ) : (
                  <pre className="text-xs text-slate-900 mt-0.5 whitespace-pre-wrap break-words">
                    {JSON.stringify(status.sidecar_health, null, 2)}
                  </pre>
                )}
              </div>
            )}
            {status.free_ram_gb !== undefined && (
              <div className="flex items-start gap-2">
                <Cpu className="h-4 w-4 text-teal-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs text-slate-500 font-medium">{t('admin.freeRam')}</p>
                  <p className="text-sm font-semibold text-slate-900">{status.free_ram_gb.toFixed(1)} GB</p>
                </div>
              </div>
            )}
            {status.commit_used_gb !== undefined && status.commit_total_gb !== undefined && (
              <div className="flex items-start gap-2">
                <HardDrive className="h-4 w-4 text-teal-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs text-slate-500 font-medium">{t('admin.commitCharge')}</p>
                  <p className="text-sm font-semibold text-slate-900">
                    {status.commit_used_gb.toFixed(1)} / {status.commit_total_gb.toFixed(1)} GB
                  </p>
                </div>
              </div>
            )}
            {status.on_ac_power !== undefined && (
              <div className="flex items-start gap-2">
                {status.on_ac_power ? (
                  <Zap className="h-4 w-4 text-teal-600 mt-0.5 shrink-0" />
                ) : (
                  <ZapOff className="h-4 w-4 text-amber-600 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="text-xs text-slate-500 font-medium">{t('admin.acPower')}</p>
                  <p className="text-sm font-semibold text-slate-900">
                    {status.on_ac_power ? t('admin.onAcPower') : t('admin.onBattery')}
                  </p>
                </div>
              </div>
            )}
            {status.profile && (
              <div className="flex items-start gap-2">
                <Power className="h-4 w-4 text-teal-600 mt-0.5 shrink-0" />
                <div>
                  <p className="text-xs text-slate-500 font-medium">{t('admin.profile')}</p>
                  <p className="text-sm font-semibold text-slate-900">{status.profile}</p>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-sm text-slate-400">{t('admin.sidecarUnknown')}</p>
        )}
      </Card>

      <Card>
        <h2 className="font-semibold text-slate-900 text-sm mb-4">{t('admin.sidecarControl')}</h2>

        {actionError && <Alert variant="error" message={actionError} className="mb-4" />}
        {actionNote && <Alert variant="success" message={actionNote} className="mb-4" />}

        <div className="space-y-4">
          <div>
            <label htmlFor="sidecar-env" className="label">
              {t('admin.environment')}
            </label>
            <select
              id="sidecar-env"
              className="input-field max-w-xs"
              value={profile}
              onChange={(e) => setProfile(e.target.value as SidecarProfile)}
              disabled={starting}
            >
              <option value="dev">{t('admin.envDev')}</option>
              <option value="prod">{t('admin.envProd')}</option>
            </select>
          </div>

          <div className="flex items-center justify-between max-w-md">
            <div>
              <p className="text-sm font-medium text-slate-900">{t('admin.warmModels')}</p>
              <p className="text-xs text-slate-500">{t('admin.warmModelsHint')}</p>
            </div>
            <Toggle checked={warm} onChange={setWarm} label={t('admin.warmModels')} disabled={starting} />
          </div>

          <label className="flex items-start gap-3 max-w-md cursor-pointer">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              disabled={starting}
              className="mt-1 h-4 w-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500"
            />
            <span>
              <span className="block text-sm font-medium text-slate-900">{t('admin.forceGuard')}</span>
              <span className="block text-xs text-slate-500">{t('admin.forceGuardHint')}</span>
            </span>
          </label>

          <div className="flex gap-3 pt-2">
            <Button onClick={handleStart} loading={starting} disabled={stopping}>
              <Play className="h-4 w-4" />
              {t('admin.start')}
            </Button>
            <Button variant="danger" onClick={handleStop} loading={stopping} disabled={starting}>
              <Square className="h-4 w-4" />
              {t('admin.stop')}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}
