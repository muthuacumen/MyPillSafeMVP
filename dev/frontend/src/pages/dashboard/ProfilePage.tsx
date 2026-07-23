import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
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
  useVoicePageAnnounce('My Profile');
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
      .catch(() => setLoadError('Could not load your profile. Please refresh and try again.'));
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
      setSaveSuccess('Profile updated.');
    } catch {
      setSaveError('Could not save your profile. Please try again.');
    }
  };

  const handleChangePassword = async () => {
    setPwError('');
    setPwSuccess('');
    if (pwForm.next !== pwForm.confirm) {
      setPwError('New passwords do not match.');
      return;
    }
    try {
      await patientsApi.changePassword(pwForm.current, pwForm.next);
      setPwSuccess('Password changed successfully.');
      setPwForm({ current: '', next: '', confirm: '' });
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { error?: { message?: string } } } } })
        ?.response?.data?.detail?.error?.message;
      setPwError(msg ?? 'Could not change your password.');
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

  return (
    <div className="space-y-6 page-enter max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">My Profile</h1>

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
              onClick={() => window.alert('Avatar uploads aren’t available yet.')}
              className="text-xs text-teal-600 hover:underline mt-1 min-h-[44px] inline-flex items-center"
            >
              Upload photo
            </button>
          </div>
          {!editing && (
            <Button variant="secondary" onClick={() => setEditing(true)}>
              <Pencil className="h-4 w-4" /> Edit Profile
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
        <SectionHeader>Medication Summary</SectionHeader>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-3">
          <StatCard
            label="Active Prescriptions"
            value={String(activeCount)}
            icon={<Pill className="h-5 w-5" strokeWidth={1.8} />}
            iconBg="bg-navy/10 text-navy"
          />
          <StatCard
            label="Last Scan"
            value={patient.last_scan_at ? new Date(patient.last_scan_at).toLocaleDateString() : '—'}
            icon={<Calendar className="h-5 w-5" strokeWidth={1.8} />}
            iconBg="bg-purple-50 text-purple-600"
          />
        </div>
        <Link to="/dashboard/medications" className="text-xs text-teal-600 hover:underline mt-2 inline-block">
          View my medications →
        </Link>
      </div>

      {/* Personal details */}
      <div>
        <SectionHeader>Personal Details</SectionHeader>
        <Card className="mt-3">
          {saveError && <div className="mb-3"><Alert variant="error" message={saveError} /></div>}
          {saveSuccess && !editing && <div className="mb-3"><Alert variant="success" message={saveSuccess} /></div>}

          {editing ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Input label="First name" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
                <Input label="Last name" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
              </div>
              <Input label="Phone number" value={form.phone_number} onChange={(e) => setForm({ ...form, phone_number: e.target.value })} />
              <div>
                <label className="label" htmlFor="preferred-language">Preferred language</label>
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
                <Button variant="secondary" onClick={() => setEditing(false)}>Cancel</Button>
                <Button onClick={handleSave}>Save</Button>
              </div>
            </div>
          ) : (
            <dl className="space-y-2.5 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Date of birth</dt><dd className="text-slate-900 font-medium">{patient.date_of_birth}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Phone</dt><dd className="text-slate-900 font-medium">{patient.phone_number || '—'}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Language</dt><dd className="text-slate-900 font-medium">{patient.preferred_language === 'fr' ? 'Français' : 'English'}</dd></div>
            </dl>
          )}
        </Card>
      </div>

      {/* Caregiver / emergency contact — no such data is collected today, so this is a safe fallback, not fabricated info */}
      <div>
        <SectionHeader>Caregiver / Emergency Contact</SectionHeader>
        <Card className="mt-3">
          <EmptyState
            icon={HeartHandshake}
            title="No caregiver or emergency contact on file"
            description="This information isn't collected yet. Contact support if you'd like to add a caregiver to your account."
          />
        </Card>
      </div>

      {/* Preferences / accessibility — read-only summary; edited from Settings to avoid duplicating that logic */}
      <div>
        <SectionHeader
          action={<Link to="/dashboard/settings" className="text-xs text-teal-600 hover:underline flex items-center gap-1"><Settings2 className="h-3 w-3" /> Edit in Settings</Link>}
        >
          Preferences &amp; Accessibility
        </SectionHeader>
        <Card className="mt-3 divide-y divide-slate-100">
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            <Globe className="h-4 w-4 text-teal-600 shrink-0" />
            <p className="text-sm text-slate-700 flex-1">Preferred language</p>
            <p className="text-sm font-medium text-slate-900">{patient.preferred_language === 'fr' ? 'Français' : 'English'}</p>
          </div>
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            {patient.notifications_enabled ? <Bell className="h-4 w-4 text-teal-600 shrink-0" /> : <BellOff className="h-4 w-4 text-slate-400 shrink-0" />}
            <p className="text-sm text-slate-700 flex-1">Medication reminders</p>
            <p className="text-sm font-medium text-slate-900">{patient.notifications_enabled ? 'On' : 'Off'}</p>
          </div>
          <div className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
            {voice.isEnabled() ? <Volume2 className="h-4 w-4 text-teal-600 shrink-0" /> : <VolumeX className="h-4 w-4 text-slate-400 shrink-0" />}
            <p className="text-sm text-slate-700 flex-1">Voice assistant</p>
            <p className="text-sm font-medium text-slate-900">{voice.isEnabled() ? 'On' : 'Off'}</p>
          </div>
        </Card>
      </div>

      <div>
        <SectionHeader>Security</SectionHeader>
        <Card className="mt-3">
          <h2 className="font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <KeyRound className="h-4 w-4 text-teal-600" /> Change Password
          </h2>
          {pwError && <div className="mb-3"><Alert variant="error" message={pwError} /></div>}
          {pwSuccess && <div className="mb-3"><Alert variant="success" message={pwSuccess} /></div>}
          <div className="space-y-4">
            <Input
              label="Current password" type="password" value={pwForm.current}
              onChange={(e) => setPwForm({ ...pwForm, current: e.target.value })}
            />
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input
                label="New password" type="password" value={pwForm.next}
                onChange={(e) => setPwForm({ ...pwForm, next: e.target.value })}
              />
              <Input
                label="Confirm new password" type="password" value={pwForm.confirm}
                onChange={(e) => setPwForm({ ...pwForm, confirm: e.target.value })}
              />
            </div>
            <Button onClick={handleChangePassword}>Update Password</Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
