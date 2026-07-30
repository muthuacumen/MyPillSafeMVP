import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Pencil, Pill, Calendar, KeyRound, HeartHandshake, Settings2, Globe, Bell, BellOff, Volume2, VolumeX } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Alert } from '@/components/ui/Alert';
import { StatCard } from '@/components/ui/StatCard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { patientsApi } from '@/api/patients';
import { prescriptionsApi } from '@/api/prescriptions';
import { useAuthStore } from '@/store/authStore';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';
import { voice } from '@/lib/voiceAssistant';
import type { Patient } from '@/types';

export default function ProfilePage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('profile.title'));
  const authUser = useAuthStore((s) => s.user);

  const [patient, setPatient] = useState<Patient | null>(null);
  const [activeCount, setActiveCount] = useState(0);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ first_name: '', last_name: '', phone_number: '', preferred_language: 'en' });
  const [saveError, setSaveError] = useState('');
  const [saveSuccess, setSaveSuccess] = useState('');

  const [pwForm, setPwForm] = useState({ current: '', next: '', confirm: '' });
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState('');
  const [loadError, setLoadError] = useState('');

  const loadProfile = () => {
    setLoadError('');
    setPatient(null);
    patientsApi.me()
      .then(({ data }) => {
        setPatient(data);
        setForm({
          first_name: data.first_name,
          last_name: data.last_name,
          phone_number: data.phone_number ?? '',
          preferred_language: data.preferred_language,
        });
      })
      .catch(() => setLoadError(t('profile.loadError')));
  };

  useEffect(() => {
    loadProfile();
    prescriptionsApi.listMine().then(({ data }) => setActiveCount(data.length)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async () => {
    setSaveError('');
    setSaveSuccess('');
    try {
      const { data } = await patientsApi.update(form);
      setPatient(data);
      setEditing(false);
      setSaveSuccess(t('profile.saved'));
    } catch {
      setSaveError(t('profile.saveError'));
    }
  };

  const handleChangePassword = async () => {
    setPwError('');
    setPwSuccess('');
    if (pwForm.next !== pwForm.confirm) {
      setPwError(t('profile.pwMismatch'));
      return;
    }
    try {
      await patientsApi.changePassword(pwForm.current, pwForm.next);
      setPwSuccess(t('profile.pwChanged'));
      setPwForm({ current: '', next: '', confirm: '' });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { error?: { message?: string } } } } })
        ?.response?.data?.detail?.error?.message;
      setPwError(msg ?? t('profile.pwError'));
    }
  };

  if (loadError) {
    return (
      <div className="max-w-3xl mx-auto py-12">
        <Card><ErrorState message={loadError} onRetry={loadProfile} /></Card>
      </div>
    );
  }

  if (!patient) {
    return (
      <div className="max-w-3xl mx-auto py-12 space-y-4">
        <LoadingSkeleton variant="card" rows={3} />
        <LoadingSkeleton variant="card" rows={2} />
      </div>
    );
  }

  const initials = `${patient.first_name[0] ?? ''}${patient.last_name[0] ?? ''}`.toUpperCase();
  // Language endonyms are deliberately NOT translated.
  const languageName = patient.preferred_language === 'fr' ? 'Français' : 'English';

  return (
    <div className="space-y-6 page-enter max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">{t('profile.title')}</h1>

      {/* Profile summary */}
      <Card>
        <div className="flex items-center gap-4">
          <div className="h-20 w-20 rounded-full bg-teal-100 border border-teal-200 flex items-center justify-center shrink-0">
            <span className="text-teal-700 text-2xl font-bold">{initials}</span>
          </div>
          <div className="flex-1">
            <p className="font-bold text-slate-900 text-lg">{patient.first_name} {patient.last_name}</p>
            <p className="text-sm text-slate-500">{authUser?.email}</p>
            <button
              type="button"
              onClick={() => window.alert(t('profile.uploadUnavailable'))}
              className="text-xs text-teal-600 hover:underline mt-1 min-h-[44px] inline-flex items-center"
            >
              {t('profile.uploadPhoto')}
            </button>
          </div>
          {!editing && (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil className="h-4 w-4" /> {t('profile.edit')}
            </Button>
          )}
        </div>
      </Card>

      {/* Medication summary -- the "Medications Analyzed" card was removed
          (Phase 6): that field was only ever incremented by the deleted
          legacy /analyze demo stub, so it read as a fabricated, frozen
          stat. The DB column/API field stay (no migration), just not
          displayed. */}
      <div>
        <SectionHeader>{t('profile.summaryTitle')}</SectionHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
          <StatCard
            label={t('profile.activePrescriptions')}
            value={String(activeCount)}
            icon={<Pill className="h-5 w-5" strokeWidth={1.8} />}
            iconBg="bg-navy/10 text-navy"
          />
          <StatCard
            label={t('profile.lastScan')}
            value={patient.last_scan_at ? new Date(patient.last_scan_at).toLocaleDateString() : '—'}
            icon={<Calendar className="h-5 w-5" strokeWidth={1.8} />}
            iconBg="bg-purple-50 text-purple-600"
          />
        </div>
        <Link to="/dashboard/medications" className="text-xs text-teal-600 hover:underline mt-2 inline-block">
          {t('profile.viewMedications')}
        </Link>
      </div>

      {/* Personal details */}
      <div>
        <SectionHeader>{t('profile.detailsTitle')}</SectionHeader>
        <Card className="mt-3">
          {saveError && <div className="mb-3"><Alert variant="error" message={saveError} /></div>}
          {saveSuccess && !editing && <div className="mb-3"><Alert variant="success" message={saveSuccess} /></div>}

          {editing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label={t('profile.firstName')} value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
                <Input label={t('profile.lastName')} value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
              </div>
              <Input label={t('profile.phoneNumber')} value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
              <div>
                <label className="label" htmlFor="preferred-language">{t('profile.preferredLanguage')}</label>
                <select
                  id="preferred-language"
                  className="input-field"
                  value={form.preferred_language}
                  onChange={(e) => setForm({ ...form, preferred_language: e.target.value })}
                >
                  <option value="en">English</option>
                  <option value="fr">Français</option>
                </select>
              </div>
              <div className="flex gap-3">
                <Button variant="secondary" onClick={() => setEditing(false)}>{t('common.cancel')}</Button>
                <Button onClick={handleSave}>{t('common.save')}</Button>
              </div>
            </div>
          ) : (
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">{t('profile.dob')}</dt><dd className="text-slate-900 font-medium">{patient.date_of_birth}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">{t('profile.phone')}</dt><dd className="text-slate-900 font-medium">{patient.phone_number || '—'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">{t('profile.language')}</dt><dd className="text-slate-900 font-medium">{languageName}</dd></div>
            </dl>
          )}
        </Card>
      </div>

      {/* Caregiver / emergency contact — no such data is collected today, so this is a safe fallback, not fabricated info */}
      <div>
        <SectionHeader>{t('profile.caregiverTitle')}</SectionHeader>
        <Card className="mt-3">
          <EmptyState
            icon={HeartHandshake}
            title={t('profile.caregiverEmptyTitle')}
            description={t('profile.caregiverEmptyBody')}
          />
        </Card>
      </div>

      {/* Preferences / accessibility — read-only summary; edited from Settings to avoid duplicating that logic */}
      <div>
        <SectionHeader
          action={<Link to="/dashboard/settings" className="text-xs text-teal-600 hover:underline flex items-center gap-1"><Settings2 className="h-3 w-3" /> {t('profile.editInSettings')}</Link>}
        >
          {t('profile.preferencesTitle')}
        </SectionHeader>
        <Card className="mt-3 divide-y divide-slate-100">
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            <Globe className="h-4 w-4 text-teal-600 shrink-0" />
            <p className="text-sm text-slate-700 flex-1">{t('profile.preferredLanguage')}</p>
            <p className="text-sm font-medium text-slate-900">{languageName}</p>
          </div>
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            {patient.notifications_enabled ? <Bell className="h-4 w-4 text-teal-600 shrink-0" /> : <BellOff className="h-4 w-4 text-slate-400 shrink-0" />}
            <p className="text-sm text-slate-700 flex-1">{t('profile.reminders')}</p>
            <p className="text-sm font-medium text-slate-900">{patient.notifications_enabled ? t('common.on') : t('common.off')}</p>
          </div>
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            {voice.isEnabled() ? <Volume2 className="h-4 w-4 text-teal-600 shrink-0" /> : <VolumeX className="h-4 w-4 text-slate-400 shrink-0" />}
            <p className="text-sm text-slate-700 flex-1">{t('profile.voiceAssistant')}</p>
            <p className="text-sm font-medium text-slate-900">{voice.isEnabled() ? t('common.on') : t('common.off')}</p>
          </div>
        </Card>
      </div>

      <div>
        <SectionHeader>{t('profile.securityTitle')}</SectionHeader>
        <Card className="mt-3">
          <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-teal-600" /> {t('profile.changePassword')}
          </h2>
          {pwError && <div className="mb-3"><Alert variant="error" message={pwError} /></div>}
          {pwSuccess && <div className="mb-3"><Alert variant="success" message={pwSuccess} /></div>}
          <div className="space-y-4">
            <Input
              label={t('profile.currentPassword')} type="password" value={pwForm.current}
              onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })}
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label={t('profile.newPassword')} type="password" value={pwForm.next}
                onChange={(e) => setPwForm({ ...pwForm, next: e.target.value })}
              />
              <Input
                label={t('profile.confirmPassword')} type="password" value={pwForm.confirm}
                onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
              />
            </div>
            <Button onClick={handleChangePassword}>{t('profile.updatePassword')}</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
