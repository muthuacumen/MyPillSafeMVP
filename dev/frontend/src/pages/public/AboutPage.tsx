import { Heart, Eye, Users, ScanLine, FileText, ShieldCheck } from 'lucide-react';
import { Card } from '@/components/ui/Card';

const TEAM = [
  { name: 'Sumanth Reddy K', role: 'Full-Stack Development & ML Pipeline' },
];

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12 space-y-10">
      <section>
        <h1 className="text-3xl font-bold text-slate-900">About PillSafe</h1>
        <p className="text-slate-600 mt-3 leading-relaxed">
          PillSafe is a medication safety application that helps patients verify their prescriptions
          and pills using AI-powered scanning. Our mission is to reduce preventable medication errors
          by making it easy for anyone — regardless of literacy, eyesight, or language — to understand
          exactly what they&apos;re taking.
        </p>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-4">Who it&apos;s for</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="text-center">
            <Users className="h-7 w-7 text-teal-600 mx-auto mb-2" />
            <p className="font-semibold text-slate-900 text-sm">Elderly Patients</p>
            <p className="text-sm text-slate-500 mt-1">Large text and voice readouts make daily medication checks simple.</p>
          </Card>
          <Card className="text-center">
            <Heart className="h-7 w-7 text-teal-600 mx-auto mb-2" />
            <p className="font-semibold text-slate-900 text-sm">Caregivers</p>
            <p className="text-sm text-slate-500 mt-1">Track and verify medications for the people you look after.</p>
          </Card>
          <Card className="text-center">
            <Eye className="h-7 w-7 text-teal-600 mx-auto mb-2" />
            <p className="font-semibold text-slate-900 text-sm">Visually Impaired</p>
            <p className="text-sm text-slate-500 mt-1">A full voice assistant reads pages, schedules, and scan results aloud.</p>
          </Card>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-4">How it works</h2>
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[
            { icon: ScanLine, label: 'Scan' },
            { icon: FileText, label: 'Read' },
            { icon: ShieldCheck, label: 'Verify' },
            { icon: Heart, label: 'Stay Safe' },
          ].map(({ icon: Icon, label }, i) => (
            <div key={label} className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0">
                <Icon className="h-5 w-5 text-teal-600" />
              </div>
              <p className="text-sm font-medium text-slate-900">{i + 1}. {label}</p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-4">Team</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {TEAM.map((member) => (
            <Card key={member.name}>
              <p className="font-semibold text-slate-900">{member.name}</p>
              <p className="text-sm text-slate-500">{member.role}</p>
            </Card>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold text-slate-900 mb-2">Academic context</h2>
        <p className="text-sm text-slate-500">
          PillSafe is built as part of the Conestoga College Graduate AI/ML program, AIML-6900 Capstone.
        </p>
      </section>
    </div>
  );
}
