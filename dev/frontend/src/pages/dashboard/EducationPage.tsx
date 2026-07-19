import { Camera, FileText, Pill, ShieldAlert, HelpCircle, AlertTriangle } from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { useVoicePageAnnounce } from '@/hooks/useVoicePageAnnounce';

const STEPS = [
  { n: 1, title: 'Open Analyze', desc: 'Go to the Analyze page from the sidebar. Your camera opens automatically.' },
  { n: 2, title: 'Take a photo', desc: 'Point your camera at the prescription label or pill, then tap Capture.' },
  { n: 3, title: 'Confirm', desc: 'Check the photo is clear and tap Confirm to send it for analysis.' },
  { n: 4, title: 'Review results', desc: 'PillSafe shows the medication details and any safety warnings.' },
];

const LABEL_PARTS = [
  'Drug name — the medication’s name, usually printed largest on the label.',
  'Dosage — how much of the medication is in each pill (e.g. 500 mg).',
  'Frequency — how often to take it (e.g. twice daily, with meals).',
  'Prescribing doctor — who prescribed the medication.',
  'Refills remaining — how many more times the pharmacy can refill it.',
  'Expiry date — do not take the medication after this date.',
];

const CAN_CANNOT = {
  can: [
    'Read prescription labels and identify common time-of-day dosing patterns.',
    'Estimate a pill’s colour, shape, and imprint from a photo.',
    'Flag when a scanned pill doesn’t match your active prescriptions.',
  ],
  cannot: [
    'Diagnose medical conditions or recommend treatment changes.',
    'Replace advice from your pharmacist or physician.',
    'Guarantee 100% accurate pill identification — always verify visually too.',
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

const FAQ = [
  { q: 'Is PillSafe a substitute for my pharmacist?', a: 'No. PillSafe is a decision support tool only — always confirm with a licensed pharmacist or physician.' },
  { q: 'Does PillSafe store my prescription photos?', a: 'Photos are stored only to support your own medication record and are scoped to your account.' },
  { q: 'What if the camera can’t read my label?', a: 'Make sure the label is well-lit and in focus, or use the upload option to choose a clearer photo.' },
  { q: 'Can a caregiver use PillSafe for someone else?', a: 'Yes, a caregiver can scan prescriptions on behalf of a patient using the same account.' },
  { q: 'What does a red warning mean?', a: 'It means the scanned pill doesn’t match anything in your active prescriptions — do not take it without checking with a pharmacist.' },
  { q: 'What does an amber reminder mean?', a: 'It means the medication matches a prescription, but it isn’t currently scheduled for this time of day.' },
  { q: 'Can I turn on voice readouts?', a: 'Yes — use the speaker icon in the top bar to toggle the voice assistant on or off.' },
  { q: 'Is my data shared with anyone else?', a: 'No prescription or scan data is shared in aggregate or with other accounts.' },
];

export default function EducationPage() {
  useVoicePageAnnounce('Medication Education');

  return (
    <div className="space-y-6 page-enter max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-slate-900">Medication Education</h1>

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Camera className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">How to use PillSafe</h2>
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
          <h2 className="font-semibold text-slate-900">What PillSafe can and cannot do</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <p className="text-sm font-semibold text-success-text mb-2">PillSafe can</p>
            <ul className="space-y-1.5">
              {CAN_CANNOT.can.map((item) => (
                <li key={item} className="text-sm text-slate-600">{item}</li>
              ))}
            </ul>
          </div>
          <div>
            <p className="text-sm font-semibold text-danger-text mb-2">PillSafe cannot</p>
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

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <HelpCircle className="h-4 w-4 text-teal-600" />
          <h2 className="font-semibold text-slate-900">Frequently Asked Questions</h2>
        </div>
        <div className="divide-y divide-slate-100">
          {FAQ.map((item) => (
            <details key={item.q} className="py-3 group">
              <summary className="font-medium text-slate-900 text-sm cursor-pointer list-none flex items-center justify-between">
                {item.q}
                <span className="text-teal-600 group-open:rotate-45 transition-transform text-lg">+</span>
              </summary>
              <p className="text-sm text-slate-500 mt-2">{item.a}</p>
            </details>
          ))}
        </div>
      </Card>
    </div>
  );
}
