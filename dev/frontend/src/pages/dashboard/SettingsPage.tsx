import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Bell, Volume2, Globe, Trash2 } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import { patientsApi } from '@/api/patients';
import { useAuth } from '@/hooks/useAuth';
import { voice } from '@/lib/voiceAssistant';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import type { Patient } from '@/types';

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-7 w-12 min-h-[28px] items-center rounded-full transition-colors ${
        checked ? 'bg-primary' : 'bg-slate-300'
      }`}
    >
      <span className={`inline-block h-5 w-5 transform rounded-full bg-white transition-transform ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

export default function SettingsPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('settings.title'));
  const { logout } = useAuth();

  const [patient, setPatient] = useState<Patient | null>(null);
  const [voiceEnabled, setVoiceEnabled] = useState(voice.isEnabled());
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    patientsApi.me()
      .then(({ data }) => setPatient(data))
      .catch(() => setError(t('settings.loadError')));
    return voice.subscribe(setVoiceEnabled);
  }, [t]);

  const updateNotifications = async (enabled: boolean) => {
    setPatient((p) => (p ? { ...p, notifications_enabled: enabled } : p));
    await patientsApi.update({ notifications_enabled: enabled }).catch(() => setError(t('settings.saveError')));
  };

  const updateLanguage = async (lang: string) => {
    setPatient((p) => (p ? { ...p, preferred_language: lang } : p));
    await patientsApi.update({ preferred_language: lang }).catch(() => setError(t('settings.saveError')));
  };

  const handleDelete = async () => {
    await patientsApi.deleteAccount();
    await logout();
  };

  if (!patient) {
    return (
      <div className="max-w-2xl mx-auto py-12 text-center">
        {error ? <Alert variant="error" message={error} /> : <p className="text-slate-400">{t('common.loading')}</p>}
      </div>
    );
  }

  return (
    <div className="space-y-6 page-enter max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">{t('settings.title')}</h1>
      {error && <Alert variant="error" message={error} />}

      <Card>
        <h2 className="font-semibold text-slate-900 mb-4">{t('settings.notificationsTitle')}</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="h-5 w-5 text-teal-600" />
            <div>
              <p className="text-sm font-medium text-slate-900">{t('settings.reminders')}</p>
              <p className="text-xs text-slate-500">{t('settings.remindersDesc')}</p>
            </div>
          </div>
          <Toggle
            checked={patient.notifications_enabled}
            onChange={updateNotifications}
            label={t('settings.reminders')}
          />
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-slate-900 mb-4">{t('settings.voiceTitle')}</h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Volume2 className="h-5 w-5 text-teal-600" />
            <div>
              <p className="text-sm font-medium text-slate-900">{t('settings.voiceLabel')}</p>
              <p className="text-xs text-slate-500">{t('settings.voiceDesc')}</p>
            </div>
          </div>
          <Toggle checked={voiceEnabled} onChange={() => voice.toggle()} label={t('settings.voiceTitle')} />
        </div>
      </Card>

      <Card>
        <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
          <Globe className="h-4 w-4 text-teal-600" /> {t('settings.languageTitle')}
        </h2>
        <select
          aria-label={t('settings.languageTitle')}
          className="input-field max-w-xs"
          value={patient.preferred_language}
          onChange={(e) => updateLanguage(e.target.value)}
        >
          {/* Language endonyms are deliberately NOT translated -- a French
              reader looks for "Français", not "French". */}
          <option value="en">English</option>
          <option value="fr">Français</option>
        </select>
      </Card>

      <Card className="border-danger-border">
        <h2 className="font-semibold text-danger-text mb-4">{t('settings.dangerTitle')}</h2>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-slate-900">{t('settings.deleteAccount')}</p>
            <p className="text-xs text-slate-500">{t('settings.deleteDesc')}</p>
          </div>
          <Button variant="danger" onClick={() => setShowDeleteConfirm(true)}>
            <Trash2 className="h-4 w-4" /> {t('settings.deleteAccount')}
          </Button>
        </div>
      </Card>

      {showDeleteConfirm && (
        <div role="dialog" aria-modal="true" className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/40 px-4">
          <Card className="max-w-sm w-full">
            <h3 className="font-semibold text-slate-900">{t('settings.deleteConfirmTitle')}</h3>
            <p className="text-sm text-slate-500 mt-2">{t('settings.deleteConfirmBody')}</p>
            <div className="flex gap-3 mt-5">
              <Button variant="secondary" onClick={() => setShowDeleteConfirm(false)} className="flex-1">
                {t('common.cancel')}
              </Button>
              <Button variant="danger" onClick={handleDelete} className="flex-1">
                {t('common.delete')}
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
