import { Camera, FileText, Pill, ShieldAlert, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/Card';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';

// Phase 6 rewrite -- matches the real 5-step flow (the old 4 steps skipped
// the prescription-confirm step entirely and described a single generic
// "scan page" that no longer exists now that scanning is split into two
// routes; see the CAN/CANNOT section below too).
//
// Phase-6 wording was verified against actual UI/backend behaviour before
// shipping: no dedicated "dosing pattern" detection exists, pill checking
// only ever verifies against the signed-in patient's own confirmed
// medications (never the full catalogue), and amber means "could not
// confirm", never a softened red (binding decision-colour rule). That
// wording now lives in `help.*` in both locale files -- only the key order
// is held here.
const STEP_KEYS = ['s1', 's2', 's3', 's4', 's5'] as const;
const LABEL_PART_KEYS = ['name', 'dosage', 'frequency', 'doctor', 'refills', 'expiry'] as const;
const CAN_KEYS = ['c1', 'c2', 'c3'] as const;
const TIP_KEYS = ['t1', 't2', 't3', 't4', 't5', 't6', 't7'] as const;

export default function EducationPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('nav.education'));

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">{t('nav.education')}</h1>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Camera className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">{t('help.howToUseTitle')}</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {STEP_KEYS.map((key, i) => (
            <div key={key} className="flex items-start gap-3">
              <div className="h-9 w-9 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0 font-bold text-teal-700">
                {i + 1}
              </div>
              <div>
                <p className="font-semibold text-slate-900 text-sm">{t(`help.steps.${key}.title`)}</p>
                <p className="text-sm text-slate-500 mt-0.5">{t(`help.steps.${key}.desc`)}</p>
                {/* The pill tray is the next step in controlled capture and is
                    still in development -- it is mentioned only here, under the
                    capture step it will change, and carries no accuracy claim. */}
                {key === 's3' && (
                  <p className="text-xs text-slate-400 mt-1.5">{t('help.trayNote')}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">{t('help.labelTitle')}</h2>
        </div>
        <ul className="space-y-2">
          {LABEL_PART_KEYS.map((key) => (
            <li key={key} className="flex items-start gap-2 text-sm text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-500 mt-2 shrink-0" />
              {t(`help.labelParts.${key}`)}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Pill className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">{t('help.canCannotTitle')}</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-semibold text-success-text mb-2">{t('help.canTitle')}</p>
            <ul className="space-y-1.5">
              {CAN_KEYS.map((key) => (
                <li key={key} className="text-sm text-slate-600">{t(`help.can.${key}`)}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-danger-text mb-2">{t('help.cannotTitle')}</p>
            <ul className="space-y-1.5">
              {CAN_KEYS.map((key) => (
                <li key={key} className="text-sm text-slate-600">{t(`help.cannot.${key}`)}</li>
              ))}
            </ul>
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-4 border-t border-slate-100 pt-3">{t('help.disclaimer')}</p>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">{t('help.tipsTitle')}</h2>
        </div>
        <ul className="space-y-2">
          {TIP_KEYS.map((key) => (
            <li key={key} className="flex items-start gap-2 text-sm text-slate-600">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
              {t(`help.tips.${key}`)}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
