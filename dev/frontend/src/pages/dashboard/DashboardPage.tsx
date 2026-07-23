import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FileText, ScanLine, ShieldCheck, Activity, Clock, ArrowRight,
  Pill, AlertTriangle, BookOpen, Bell, BellOff,
  Sunrise, Sun, Sunset, Moon, CheckCircle2, Hourglass, CalendarClock,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { SectionHeader } from '@/components/ui/SectionHeader';
import { EmptyState } from '@/components/ui/EmptyState';
import { ErrorState } from '@/components/ui/ErrorState';
import { LoadingSkeleton } from '@/components/ui/LoadingSkeleton';
import { TimeAwareHeader } from '@/components/dashboard/TimeAwareHeader';
import { useAuthStore } from '@/store/authStore';
import { prescriptionsApi } from '@/api/prescriptions';
import { patientsApi } from '@/api/patients';
import { scansApi } from '@/api/scans';
import { voice } from '@/lib/voiceAssistant';
import type { Patient, Prescription, ScanRecord, TimeSlot } from '@/types';

const SCHEDULE_BADGE: Record<TimeSlot, string> = {
  morning: 'schedule-badge-morning',
  afternoon: 'schedule-badge-afternoon',
  evening: 'schedule-badge-evening',
  night: 'schedule-badge-night',
};

const SCHEDULE_ROW: Record<TimeSlot, string> = {
  morning: 'schedule-row-morning',
  afternoon: 'schedule-row-afternoon',
  evening: 'schedule-row-evening',
  night: 'schedule-row-night',
};

const SLOT_ICON: Record<TimeSlot, LucideIcon> = {
  morning: Sunrise,
  afternoon: Sun,
  evening: Sunset,
  night: Moon,
};

const SLOT_HERO: Record<TimeSlot, string> = {
  morning: 'border-amber-300 from-amber-50',
  afternoon: 'border-orange-300 from-orange-50',
  evening: 'border-rose-300 from-rose-50',
  // Phase 6 palette sweep: was border-indigo-300/from-indigo-50 (off-brand
  // blue-purple) -- moved onto the Phase 5 navy token.
  night: 'border-navy/30 from-light',
};

const SLOT_HERO_ICON_BG: Record<TimeSlot, string> = {
  morning: 'bg-amber-500',
  afternoon: 'bg-orange-500',
  evening: 'bg-rose-500',
  // Phase 6 palette sweep: was bg-indigo-500.
  night: 'bg-navy',
};

/** 20-minute window either side of "now" counts as due, not upcoming/past. */
const DUE_WINDOW_MIN = 20;

interface DoseRow {
  prescription: Prescription;
  time: string;
  label: string;
  slot: TimeSlot;
}

/** Buckets a clock hour into a day-part purely from the time itself — a
 * medication's stored time_slots reflects its overall frequency category
 * (e.g. TID -> morning+afternoon+evening), not which slot any one of its
 * several specific_times actually falls in, so each dose row needs its
 * own slot computed from its own time. */
function slotForTime(hhmm: string): TimeSlot {
  const [h] = hhmm.split(':').map(Number);
  if (h >= 5 && h < 12) return 'morning';
  if (h >= 12 && h < 17) return 'afternoon';
  if (h >= 17 && h < 20) return 'evening';
  return 'night';
}

function buildTodaysDoses(prescriptions: Prescription[]): DoseRow[] {
  const rows: DoseRow[] = [];
  for (const p of prescriptions) {
    for (const time of p.specific_times) {
      const [h, m] = time.split(':').map(Number);
      const suffix = h < 12 ? 'AM' : 'PM';
      const h12 = h % 12 || 12;
      rows.push({
        prescription: p,
        time,
        label: `${h12}:${String(m).padStart(2, '0')} ${suffix}`,
        slot: slotForTime(time),
      });
    }
  }
  return rows.sort((a, b) => a.time.localeCompare(b.time));
}

function findNextDose(rows: DoseRow[]): { row: DoseRow; minutesUntil: number } | null {
  if (rows.length === 0) return null;
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  let best: { row: DoseRow; minutesUntil: number } | null = null;
  for (const row of rows) {
    const [h, m] = row.time.split(':').map(Number);
    const rowMinutes = h * 60 + m;
    const delta = rowMinutes >= nowMinutes ? rowMinutes - nowMinutes : rowMinutes + 1440 - nowMinutes;
    if (!best || delta < best.minutesUntil) best = { row, minutesUntil: delta };
  }
  return best;
}

/** Schedule status only — PillSafe doesn't record dose confirmations, so this
 * reflects clock time vs. each dose's scheduled time, not verified adherence. */
function bucketScheduleStatus(rows: DoseRow[]): { upcoming: number; due: number; past: number } {
  const now = new Date();
  const nowMinutes = now.getHours() * 60 + now.getMinutes();
  let upcoming = 0;
  let due = 0;
  let past = 0;
  for (const row of rows) {
    const [h, m] = row.time.split(':').map(Number);
    const rowMinutes = h * 60 + m;
    const delta = rowMinutes - nowMinutes;
    if (Math.abs(delta) <= DUE_WINDOW_MIN) due += 1;
    else if (delta > 0) upcoming += 1;
    else past += 1;
  }
  return { upcoming, due, past };
}

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const { t } = useTranslation();
  const firstName = user?.first_name ?? 'there';

  const [prescriptions, setPrescriptions] = useState<Prescription[] | null>(null);
  const [prescriptionsError, setPrescriptionsError] = useState('');
  const [patient, setPatient] = useState<Patient | null>(null);
  const [scans, setScans] = useState<ScanRecord[] | null>(null);
  const [scansError, setScansError] = useState('');

  const loadPrescriptions = useCallback(() => {
    setPrescriptionsError('');
    setPrescriptions(null);
    prescriptionsApi.listMine()
      .then(({ data }) => {
        setPrescriptions(data);
        voice.speak(`Good morning ${firstName}. You have ${data.length} medication${data.length === 1 ? '' : 's'} scheduled today.`);
      })
      .catch(() => setPrescriptionsError('Could not load your medication schedule.'));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadScans = useCallback(() => {
    setScansError('');
    setScans(null);
    scansApi.listMine()
      .then(({ data }) => setScans(data))
      .catch(() => setScansError('Could not load safety records.'));
  }, []);

  useEffect(() => {
    loadPrescriptions();
    loadScans();
    patientsApi.me().then(({ data }) => setPatient(data)).catch(() => {});
  }, [loadPrescriptions, loadScans]);

  // Live countdown — re-render every 30s so "in 12 minutes" and the schedule
  // status buckets stay accurate. Kept separate from TimeAwareHeader's 1s
  // clock so the schedule/stat cards below don't re-render every second.
  const [, forceTick] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => forceTick((n) => n + 1), 30_000);
    return () => window.clearInterval(id);
  }, []);

  const todaysDoses = buildTodaysDoses(prescriptions ?? []);
  const nextDose = findNextDose(todaysDoses);
  const hasSchedule = todaysDoses.length > 0;
  const scheduleStatus = bucketScheduleStatus(todaysDoses);
  const safetyAlerts = (scans ?? []).filter((s) => s.match_status !== 'matched').slice(0, 3);

  const quickActions = [
    // Phase 6: the single "Check My Pill" tile split into its two real
    // scan modes (AnalyzePage's in-page switcher was removed; mode is now
    // routed -- see router/index.tsx).
    { to: '/dashboard/scan-prescription', icon: FileText, label: t('dashboard.actions.scanRx'), desc: t('dashboard.actions.scanRxDesc'), badge: null, accent: 'group-hover:text-teal-600' },
    { to: '/dashboard/scan-pill', icon: ScanLine, label: t('dashboard.actions.scanPill'), desc: t('dashboard.actions.scanPillDesc'), badge: null, accent: 'group-hover:text-teal-600' },
    { to: '/dashboard/medications', icon: Pill, label: t('dashboard.actions.medications'), desc: t('dashboard.actions.medicationsDesc'), badge: null, accent: 'group-hover:text-teal-600' },
    // Phase 6 palette sweep: accent was group-hover:text-blue-600 (off-brand) -- moved to navy.
    { to: '/dashboard/safety', icon: ShieldCheck, label: t('dashboard.actions.safety'), desc: t('dashboard.actions.safetyDesc'), badge: null, accent: 'group-hover:text-navy' },
    { to: '/dashboard/education', icon: BookOpen, label: t('dashboard.actions.education'), desc: t('dashboard.actions.educationDesc'), badge: null, accent: 'group-hover:text-purple-600' },
  ];

  const safetyTips = [
    { icon: Clock, tip: t('dashboard.tips.routine') },
    { icon: AlertTriangle, tip: t('dashboard.tips.crush') },
    { icon: Activity, tip: t('dashboard.tips.list') },
  ];

  return (
    <div className="space-y-6 page-enter max-w-6xl mx-auto">
      <TimeAwareHeader firstName={firstName} tagline={t('dashboard.tagline')} analyzeLabel={t('dashboard.analyzeNow')} />

      {/* Stats -- the "Medications Analyzed" card was removed (Phase 6):
          that field was only ever incremented by the deleted legacy
          /analyze demo stub, so it read as a fabricated, frozen stat.
          The DB column/API field stay (no migration), just not displayed. */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          label={t('dashboard.stats.safetyScore')}
          value="—"
          sub={t('dashboard.stats.safetyScoreSub')}
          icon={<ShieldCheck className="h-5 w-5" strokeWidth={1.8} />}
          iconBg="bg-navy/10 text-navy"
        />
        {/* Phase 6: replaced "Interactions Found" (implied an interaction-checker
            the app doesn't have) with a real, computed stat from scan history. */}
        <StatCard
          label={t('dashboard.stats.verified')}
          value={scans === null ? '—' : String(scans.filter((s) => s.match_status === 'matched').length)}
          sub={t('dashboard.stats.verifiedSub')}
          icon={<ShieldCheck className="h-5 w-5" strokeWidth={1.8} />}
          iconBg="bg-teal-50 text-teal-600"
        />
        <StatCard
          label={t('dashboard.stats.adherence')}
          value="—"
          sub={t('dashboard.stats.adherenceSub')}
          icon={<Activity className="h-5 w-5" strokeWidth={1.8} />}
          iconBg="bg-purple-50 text-purple-600"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-4">
          <SectionHeader>{t('dashboard.quickActions')}</SectionHeader>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {quickActions.map(({ to, icon: Icon, label, desc, badge, accent }) => (
              <Link
                key={to}
                to={to}
                className="group card p-5 hover:border-teal-300 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md"
              >
                <div className="flex items-start justify-between">
                  <Icon className={`h-6 w-6 text-slate-400 transition-colors duration-200 ${accent}`} strokeWidth={1.6} />
                  {badge && <span className="badge bg-teal-50 text-teal-600 border border-teal-200">{badge}</span>}
                </div>
                <p className="mt-4 font-semibold text-slate-900 text-sm">{label}</p>
                <p className="mt-1 text-xs text-slate-500">{desc}</p>
                <div className="mt-3 flex items-center gap-1 text-xs text-slate-400 group-hover:text-teal-600 transition-colors">
                  {t('dashboard.open')} <ArrowRight className="h-3 w-3" />
                </div>
              </Link>
            ))}
          </div>

          {prescriptionsError ? (
            <Card>
              <ErrorState message={prescriptionsError} onRetry={loadPrescriptions} />
            </Card>
          ) : prescriptions === null ? (
            <>
              <LoadingSkeleton variant="card" rows={2} />
              <LoadingSkeleton variant="list" rows={3} />
            </>
          ) : !hasSchedule ? (
            <Card>
              <EmptyState
                icon={Pill}
                title="No medications scheduled yet"
                description="Scan a prescription label to start tracking your daily schedule and reminders."
                action={
                  <Link to="/dashboard/scan-prescription" className="btn-primary min-h-[44px]">
                    <ScanLine className="h-4 w-4" /> Scan a prescription
                  </Link>
                }
              />
            </Card>
          ) : (
            <>
              {/* Next dose hero */}
              {nextDose && (
                <Card className={`border-2 bg-gradient-to-br to-white overflow-hidden ${SLOT_HERO[nextDose.row.slot]}`}>
                  <div className="flex items-center gap-5">
                    <div className={`h-20 w-20 rounded-2xl flex items-center justify-center shrink-0 shadow-md ${SLOT_HERO_ICON_BG[nextDose.row.slot]}`}>
                      {(() => {
                        const Icon = SLOT_ICON[nextDose.row.slot];
                        return <Icon className="h-10 w-10 text-white" />;
                      })()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-bold text-slate-500 uppercase tracking-wide">Next dose</p>
                      <p className="text-3xl font-extrabold text-slate-900 mt-1 truncate">
                        {nextDose.row.prescription.drug_name}
                        {nextDose.row.prescription.dosage ? ` · ${nextDose.row.prescription.dosage}` : ''}
                      </p>
                      <p className="text-lg font-semibold text-slate-600 mt-1">
                        {nextDose.row.label} ·{' '}
                        {nextDose.minutesUntil < 60
                          ? `in ${nextDose.minutesUntil} min`
                          : `in ${Math.floor(nextDose.minutesUntil / 60)}h ${nextDose.minutesUntil % 60}m`}
                      </p>
                    </div>
                  </div>
                </Card>
              )}

              {/* Today's schedule status — clock-time only, not a verified adherence log */}
              <div className="grid grid-cols-3 gap-3">
                <Card padding="sm" className="text-center">
                  <Hourglass className="h-4 w-4 text-slate-400 mx-auto" />
                  <p className="text-xl font-bold text-slate-900 mt-1">{scheduleStatus.upcoming}</p>
                  <p className="text-xs text-slate-500">Upcoming</p>
                </Card>
                <Card padding="sm" className="text-center border-teal-200 bg-teal-50/40">
                  <CalendarClock className="h-4 w-4 text-teal-600 mx-auto" />
                  <p className="text-xl font-bold text-teal-700 mt-1">{scheduleStatus.due}</p>
                  <p className="text-xs text-teal-700">Due now</p>
                </Card>
                <Card padding="sm" className="text-center">
                  <CheckCircle2 className="h-4 w-4 text-slate-400 mx-auto" />
                  <p className="text-xl font-bold text-slate-900 mt-1">{scheduleStatus.past}</p>
                  <p className="text-xs text-slate-500">Past</p>
                </Card>
              </div>

              <Card className="overflow-hidden">
                <div className="px-5 py-4 border-b border-slate-100">
                  <h3 className="text-lg font-bold text-slate-900">{t('dashboard.todaySchedule')}</h3>
                </div>
                <div className="px-5 py-5">
                  <div className="space-y-3">
                    {todaysDoses.map((row) => {
                      const Icon = SLOT_ICON[row.slot];
                      const isNext = nextDose?.row === row;
                      return (
                        <div
                          key={`${row.prescription.id}-${row.time}`}
                          className={`flex items-center gap-4 py-4 px-5 rounded-xl border transition-colors ${
                            isNext
                              ? 'bg-teal-50 border-teal-300 ring-2 ring-teal-200'
                              : SCHEDULE_ROW[row.slot]
                          }`}
                        >
                          <span className="text-lg font-bold text-slate-800 w-20 shrink-0">{row.label}</span>
                          <span
                            className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-sm font-bold shrink-0 ${SCHEDULE_BADGE[row.slot]}`}
                          >
                            <Icon className="h-4 w-4" />
                            {row.slot.charAt(0).toUpperCase() + row.slot.slice(1)}
                          </span>
                          <span className="text-lg text-slate-800 font-medium truncate">
                            {row.prescription.drug_name}
                            {row.prescription.dosage ? (
                              <span className="text-slate-400 font-normal"> · {row.prescription.dosage}</span>
                            ) : (
                              ''
                            )}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </Card>
            </>
          )}
        </div>

        <div className="space-y-4">
          <SectionHeader>Safety alerts</SectionHeader>
          {scansError ? (
            <Card padding="sm"><ErrorState message={scansError} onRetry={loadScans} /></Card>
          ) : scans === null ? (
            <LoadingSkeleton variant="list" rows={2} />
          ) : safetyAlerts.length === 0 ? (
            <Card padding="sm" className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-lg bg-success-bg flex items-center justify-center shrink-0">
                <ShieldCheck className="h-4 w-4 text-success-text" />
              </div>
              <p className="text-xs text-slate-600">No safety alerts — your recent scans matched your prescriptions.</p>
            </Card>
          ) : (
            <div className="space-y-2.5">
              {safetyAlerts.map((s) => (
                <Card key={s.id} padding="sm" className="flex items-start gap-3 border-warning-border bg-warning-bg/40">
                  <AlertTriangle className="h-4 w-4 text-warning-text shrink-0 mt-0.5" />
                  <div>
                    <p className="text-xs font-semibold text-slate-900">{s.drug_name ?? 'Unrecognized scan'}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{s.action_taken}</p>
                  </div>
                </Card>
              ))}
            </div>
          )}

          <SectionHeader>Reminders</SectionHeader>
          <Card padding="sm" className="flex items-center gap-3">
            <div className={`h-8 w-8 rounded-lg flex items-center justify-center shrink-0 ${patient?.notifications_enabled ? 'bg-teal-50' : 'bg-slate-100'}`}>
              {patient?.notifications_enabled ? (
                <Bell className="h-4 w-4 text-teal-600" />
              ) : (
                <BellOff className="h-4 w-4 text-slate-400" />
              )}
            </div>
            <div>
              <p className="text-xs font-semibold text-slate-900">
                {patient ? (patient.notifications_enabled ? 'Reminders are on' : 'Reminders are off') : 'Loading…'}
              </p>
              <p className="text-xs text-slate-500 mt-0.5">
                <Link to="/dashboard/settings" className="text-teal-600 hover:underline">Manage in Settings</Link>
              </p>
            </div>
          </Card>

          <SectionHeader>{t('dashboard.safetyTips')}</SectionHeader>
          <div className="space-y-3">
            {safetyTips.map(({ icon: Icon, tip }) => (
              <Card key={tip} padding="sm" className="flex items-start gap-3 hover:border-teal-200 transition-colors">
                <div className="h-7 w-7 rounded-lg bg-teal-50 flex items-center justify-center shrink-0">
                  <Icon className="h-3.5 w-3.5 text-teal-600" strokeWidth={1.8} />
                </div>
                <p className="text-xs text-slate-600 leading-relaxed">{tip}</p>
              </Card>
            ))}
          </div>

          {/* Recent activity — reuses the same scan fetch as Safety alerts */}
          <div className="card overflow-hidden">
            <div className="px-3.5 py-2.5 border-b border-slate-100 flex items-center justify-between">
              <h2 className="font-semibold text-slate-900 text-xs">{t('dashboard.recentActivity')}</h2>
              <Link to="/dashboard/safety" className="text-[11px] text-teal-600 hover:text-teal-700 transition-colors">{t('dashboard.viewAll')}</Link>
            </div>
            <div className="p-3">
              {scans === null ? (
                <LoadingSkeleton variant="list" rows={2} />
              ) : scans.length === 0 ? (
                <div className="flex items-start gap-2.5 py-1">
                  <div className="h-6 w-6 rounded-md bg-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                    <Pill className="h-3 w-3" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-slate-500">{t('dashboard.noScans')}</p>
                    <p className="text-[11px] text-slate-400 mt-0.5">{t('dashboard.noScansSub')}</p>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {scans.slice(0, 3).map((s) => (
                    <div key={s.id} className="flex items-start gap-2.5 py-1">
                      <div className="h-6 w-6 rounded-md bg-slate-100 flex items-center justify-center text-slate-400 shrink-0">
                        <Pill className="h-3 w-3" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-medium text-slate-700 truncate">{s.drug_name ?? 'Unrecognized scan'}</p>
                        <p className="text-[11px] text-slate-400 mt-0.5">{new Date(s.created_at).toLocaleDateString()}</p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
