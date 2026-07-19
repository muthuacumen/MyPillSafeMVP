import { voice } from '@/lib/voiceAssistant';
import { prescriptionsApi } from '@/api/prescriptions';
import type { Prescription } from '@/types';

const ALERT_WINDOW_MIN = 30;
const POLL_INTERVAL_MS = 30_000;
const FIRED_KEY = 'dose_reminders_fired';

interface DoseEvent {
  prescriptionId: string;
  drugName: string;
  dosage: string | null;
  doseTime: Date;
  kind: 'pre' | 'at';
}

function computeTodaysDoseEvents(prescriptions: Prescription[]): DoseEvent[] {
  const events: DoseEvent[] = [];
  const now = new Date();
  for (const p of prescriptions) {
    if (!p.is_active) continue;
    for (const time of p.specific_times) {
      const [h, m] = time.split(':').map(Number);
      const doseTime = new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0, 0);
      events.push({ prescriptionId: p.id, drugName: p.drug_name, dosage: p.dosage, doseTime, kind: 'at' });
      const preTime = new Date(doseTime.getTime() - ALERT_WINDOW_MIN * 60_000);
      events.push({ prescriptionId: p.id, drugName: p.drug_name, dosage: p.dosage, doseTime: preTime, kind: 'pre' });
    }
  }
  return events;
}

function eventKey(e: DoseEvent): string {
  return `${e.prescriptionId}-${e.kind}-${e.doseTime.toISOString().slice(0, 16)}`;
}

function getFired(): Set<string> {
  try {
    const raw = sessionStorage.getItem(FIRED_KEY);
    return raw ? new Set(JSON.parse(raw)) : new Set();
  } catch {
    return new Set();
  }
}

function markFired(key: string): void {
  const fired = getFired();
  fired.add(key);
  try {
    sessionStorage.setItem(FIRED_KEY, JSON.stringify(Array.from(fired)));
  } catch {
    /* sessionStorage unavailable — alerts will just re-fire on reload, acceptable degradation */
  }
}

function fireAlert(e: DoseEvent): void {
  const timeLabel = e.doseTime.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const text =
    e.kind === 'pre'
      ? `Reminder: ${e.drugName}${e.dosage ? ` ${e.dosage}` : ''} is due in 30 minutes, at ${timeLabel}.`
      : `It's time to take ${e.drugName}${e.dosage ? ` ${e.dosage}` : ''}.`;

  if (typeof Notification !== 'undefined' && Notification.permission === 'granted') {
    new Notification('PillSafe', { body: text, tag: eventKey(e) });
  }
  if (voice.isEnabled()) {
    voice.speak(text);
  }
}

let intervalHandle: number | null = null;

export function startDoseReminderEngine(): () => void {
  if (intervalHandle !== null) {
    return () => stopDoseReminderEngine();
  }

  if (typeof Notification !== 'undefined' && Notification.permission === 'default') {
    Notification.requestPermission().catch(() => {
      /* ignore — alerts just fall back to voice-only */
    });
  }

  const tick = async () => {
    try {
      const { data: prescriptions } = await prescriptionsApi.listMine();
      const events = computeTodaysDoseEvents(prescriptions);
      const fired = getFired();
      const now = Date.now();
      for (const e of events) {
        const key = eventKey(e);
        if (fired.has(key)) continue;
        if (now >= e.doseTime.getTime()) {
          fireAlert(e);
          markFired(key);
        }
      }
    } catch {
      /* listMine() failure (e.g. logged out, admin session) — skip this tick silently */
    }
  };

  tick();
  intervalHandle = window.setInterval(tick, POLL_INTERVAL_MS);

  return () => stopDoseReminderEngine();
}

export function stopDoseReminderEngine(): void {
  if (intervalHandle !== null) {
    window.clearInterval(intervalHandle);
    intervalHandle = null;
  }
}
