import { Camera, FileText, Pill, ShieldAlert, AlertTriangle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card } from '@/components/ui/Card';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';

// Phase 6 rewrite -- matches the real 5-step flow (the old 4 steps skipped
// the prescription-confirm step entirely and described a single generic
// "scan page" that no longer exists now that scanning is split into two
// routes; see EducationPage's CAN/CANNOT section below too).
const STEPS = [
  {
    n: 1,
    title: 'Scan your prescription',
    desc: 'Use Scan Prescription to photograph your prescription label. MyPillSafe reads it and proposes the medications it found.',
  },
  {
    n: 2,
    title: 'Confirm your medications',
    desc: 'The "Is this your medication?" panel suggests matching Canadian products for each one — you confirm the match with a tap. Nothing is added to your profile automatically.',
  },
  {
    n: 3,
    title: 'Check a pill before taking it',
    desc: 'Use Scan Pill to photograph a loose pill on the capture card. MyPillSafe checks it against your confirmed medications.',
  },
  {
    n: 4,
    title: 'Read the result',
    desc: 'Green means verified, red means it doesn’t match anything you take, and amber means MyPillSafe isn’t sure and wants you to double-check. The first pill scan can take up to a minute.',
  },
  {
    n: 5,
    title: 'Ask questions',
    desc: 'Use "Ask about my medication" for cited answers from Health Canada product monographs, in your language.',
  },
];

const LABEL_PARTS = [
  'Drug name — the medication’s name, usually printed largest on the label.',
  'Dosage — how much of the medication is in each pill (e.g. 500 mg).',
  'Frequency — how often to take it (e.g. twice daily, with meals).',
  'Prescribing doctor — who prescribed the medication.',
  'Refills remaining — how many more times the pharmacy can refill it.',
  'Expiry date — do not take the medication after this date.',
];

// Phase 6 rewrite (Muthu flagged the old list as obsolete/inaccurate) --
// wording verified against the actual UI/backend behaviour before shipping:
// no dedicated "dosing pattern" detection exists, pill checking only ever
// verifies against the signed-in patient's own confirmed medications (never
// the full catalogue), and amber means "could not confirm", never a
// softened red (binding decision-colour rule).
const CAN_CANNOT = {
  can: [
    'Read prescription labels and suggest medication matches for you to confirm.',
    'Check a photographed pill against YOUR confirmed medication list — colour, shape, and imprint.',
    'Answer medication questions with citations from Health Canada product monographs, in English or French.',
  ],
  cannot: [
    'Identify an unknown pill from the entire drug catalogue — it verifies against your own list only.',
    'Tell you it’s certain when it isn’t — amber means it could not confirm, not a softer warning.',
    'Give dosing advice, or diagnose or replace your pharmacist or physician.',
  ],
};

const TIPS = [
  'Take medications at the same time each day to build a routine.',
  'Never crush or split pills without asking your pharmacist first.',
  'Keep an updated medication list with you at all times.',
  'Store medications away from heat, light, and humidity.',
  'Never share prescription medication with another person.',
  'Check expiry dates regularly and dispose of expired medication safely.',
  'Tell every doctor and pharmacist about all medications you currently take.',
];

export default function EducationPage() {
  const { t } = useTranslation();
  useVoicePageAnnounce(t('nav.education'));

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">{t('nav.education')}</h1>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Camera className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">How to use MyPillSafe</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {STEPS.map((s) => (
            <div key={s.n} className="flex items-start gap-3">
              <div className="h-9 w-9 rounded-full bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0 font-bold text-teal-700">
                {s.n}
              </div>
              <div>
                <p className="font-semibold text-slate-900 text-sm">{s.title}</p>
                <p className="text-sm text-slate-500 mt-0.5">{s.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <FileText className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">How to read your prescription label</h2>
        </div>
        <ul className="space-y-2">
          {LABEL_PARTS.map((part) => (
            <li key={part} className="flex items-start gap-2 text-sm text-slate-600">
              <span className="h-1.5 w-1.5 rounded-full bg-teal-500 mt-2 shrink-0" />
              {part}
            </li>
          ))}
        </ul>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Pill className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">What MyPillSafe can and cannot do</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-semibold text-success-text mb-2">MyPillSafe can</p>
            <ul className="space-y-1.5">
              {CAN_CANNOT.can.map((item) => (
                <li key={item} className="text-sm text-slate-600">{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-danger-text mb-2">MyPillSafe cannot</p>
            <ul className="space-y-1.5">
              {CAN_CANNOT.cannot.map((item) => (
                <li key={item} className="text-sm text-slate-600">{item}</li>
              ))}
            </ul>
          </div>
        </div>
        <p className="text-xs text-slate-400 mt-4 border-t border-slate-100 pt-3">
          Decision support only. Always confirm medication information with a licensed pharmacist or physician.
        </p>
      </Card>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <ShieldAlert className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">Medication safety tips</h2>
        </div>
        <ul className="space-y-2">
          {TIPS.map((tip) => (
            <li key={tip} className="flex items-start gap-2 text-sm text-slate-600">
              <AlertTriangle className="h-3.5 w-3.5 text-amber-500 mt-0.5 shrink-0" />
              {tip}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
