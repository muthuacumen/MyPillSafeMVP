import { Link } from 'react-router-dom';
import {
  ScanLine, ShieldCheck, BookOpen, Bell, Heart, Users, Eye, ArrowRight,
  CheckCircle2, Clock, AlertTriangle, Ear, Type, MousePointerClick,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { useAuthStore } from '@/store/authStore';

const HOW_IT_WORKS = [
  { n: 1, icon: ScanLine, title: 'Scan', desc: 'Photograph your prescription label or a loose pill with your camera.' },
  { n: 2, icon: ShieldCheck, title: 'Verify', desc: 'PillSafe checks it against your active prescriptions for a safety match.' },
  { n: 3, icon: BookOpen, title: 'Guide', desc: 'Get plain-language, multilingual instructions on what it is and how to take it.' },
  { n: 4, icon: Bell, title: 'Remind', desc: 'Voice and on-screen reminders keep every dose on schedule.' },
];

const SAFETY_SUPPORT = [
  { icon: CheckCircle2, title: 'Wrong-dose prevention', desc: 'Every scan is checked against your active prescriptions before you take anything.' },
  { icon: Clock, title: 'Missed-dose reminders', desc: 'Automatic voice and visual reminders while the app is open, tuned to your schedule.' },
  { icon: AlertTriangle, title: 'Clear, calm warnings', desc: 'Green, amber, and red safety states — always paired with plain text, never color alone.' },
];

const CAREGIVER_SUPPORT = [
  { icon: Users, title: 'Built for caregivers', desc: 'Track schedules and safety status for the people you look after, in one place.' },
  { icon: Heart, title: 'Less anxiety, more confidence', desc: 'Know a medication has been checked instead of guessing or double-checking labels by hand.' },
];

const ACCESSIBILITY = [
  { icon: Type, title: 'Large, readable text', desc: 'Bigger base font sizes designed for elderly and low-vision users.' },
  { icon: Ear, title: 'Voice assistant', desc: 'Pages, results, and reminders can be read aloud in English, French, Arabic, and Spanish.' },
  { icon: MousePointerClick, title: 'Easy to navigate', desc: 'Large tap targets, visible focus states, and simple, uncluttered screens.' },
];

export default function LandingPage() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const primaryCta = isAuthenticated
    ? { to: '/dashboard', label: 'Open Dashboard' }
    : { to: '/register', label: 'Get Started Free' };
  const secondaryCta = isAuthenticated
    ? { to: '/dashboard/analyze', label: 'Check Medication' }
    : { to: '/register', label: 'Check Medication' };

  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-teal-600 via-teal-700 to-teal-800 text-white">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/5" />
        <div className="absolute -left-16 bottom-0 h-64 w-64 rounded-full bg-white/5" />
        <div className="relative max-w-6xl mx-auto px-6 py-20 lg:py-28 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div className="text-center lg:text-left">
            <span className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-xs font-semibold text-teal-50">
              <ShieldCheck className="h-3.5 w-3.5" /> AI-powered medication safety
            </span>
            <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight mt-5">
              Know what you&apos;re taking,<br className="hidden sm:block" /> before you take it.
            </h1>
            <p className="mt-5 text-teal-50/90 max-w-xl mx-auto lg:mx-0 text-lg leading-relaxed">
              PillSafe helps prevent wrong doses, missed doses, and medication mix-ups — and eases
              the worry caregivers carry — with a quick camera scan and clear, plain-language guidance.
            </p>
            <div className="mt-8 flex flex-wrap items-center justify-center lg:justify-start gap-4">
              <Link
                to={primaryCta.to}
                className="inline-flex items-center gap-2 bg-white text-teal-700 px-6 py-3 rounded-xl font-semibold hover:bg-teal-50 transition-colors shadow-lg min-h-[44px]"
              >
                {primaryCta.label} <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                to={secondaryCta.to}
                className="inline-flex items-center gap-2 bg-white/10 border border-white/30 text-white px-6 py-3 rounded-xl font-semibold hover:bg-white/20 transition-colors min-h-[44px]"
              >
                <ScanLine className="h-4 w-4" /> {secondaryCta.label}
              </Link>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 text-teal-50 px-2 py-3 font-semibold hover:text-white transition-colors min-h-[44px]"
              >
                See How PillSafe Works
              </a>
            </div>
            <p className="mt-6 text-xs text-teal-100/70">
              Decision support only — always confirm with a licensed pharmacist or physician.
            </p>
          </div>

          {/* Premium hero visual mockup — CSS only, no image assets */}
          <div className="relative mx-auto max-w-sm w-full" aria-hidden="true">
            <div className="rounded-3xl bg-white text-slate-900 shadow-2xl p-6 rotate-1">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Scan result</span>
                <span className="badge bg-success-bg text-success-text border border-success-border">
                  <ShieldCheck className="h-3 w-3 mr-1" /> Verified safe
                </span>
              </div>
              <div className="mt-4 flex items-center gap-3">
                <div className="h-12 w-12 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center shrink-0">
                  <ScanLine className="h-6 w-6 text-teal-600" />
                </div>
                <div>
                  <p className="font-bold text-slate-900">Metformin 500mg</p>
                  <p className="text-xs text-slate-500">Matches your active prescription</p>
                </div>
              </div>
              <div className="mt-5 pt-4 border-t border-slate-100 space-y-2.5">
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Clock className="h-4 w-4 text-slate-400" /> Next dose · 6:00 PM · with food
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <Bell className="h-4 w-4 text-slate-400" /> Reminder scheduled
                </div>
              </div>
            </div>
            <div className="absolute -bottom-6 -left-6 rounded-2xl bg-white shadow-xl p-4 -rotate-3 hidden sm:block">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-lg bg-blue-50 border border-blue-200 flex items-center justify-center">
                  <Heart className="h-4 w-4 text-blue-600" />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-900">Caregiver notified</p>
                  <p className="text-[11px] text-slate-400">All doses on track today</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Why PillSafe matters */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">Why PillSafe matters</h2>
          <p className="text-slate-500 mt-3">
            Medication mix-ups are common and stressful — for patients managing multiple prescriptions
            and for the caregivers supporting them. PillSafe brings clarity to every dose.
          </p>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {SAFETY_SUPPORT.map(({ icon: Icon, title, desc }) => (
            <Card key={title} className="text-center">
              <div className="h-12 w-12 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-3">
                <Icon className="h-6 w-6 text-teal-600" />
              </div>
              <p className="font-semibold text-slate-900">{title}</p>
              <p className="text-sm text-slate-500 mt-1.5">{desc}</p>
            </Card>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how-it-works" className="bg-white border-y border-slate-200 scroll-mt-16">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 text-center mb-10">How it works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-6">
            {HOW_IT_WORKS.map(({ n, icon: Icon, title, desc }, i) => (
              <div key={n} className="relative">
                <Card className="text-center h-full">
                  <div className="h-12 w-12 rounded-xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-3">
                    <Icon className="h-6 w-6 text-teal-600" />
                  </div>
                  <p className="font-semibold text-slate-900">{n}. {title}</p>
                  <p className="text-sm text-slate-500 mt-1.5">{desc}</p>
                </Card>
                {i < HOW_IT_WORKS.length - 1 && (
                  <ArrowRight className="hidden sm:block absolute top-1/2 -right-4 -translate-y-1/2 h-5 w-5 text-slate-300" />
                )}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Caregiver support */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div>
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">Caregiver support</h2>
            <p className="text-slate-500 mt-3 leading-relaxed">
              Looking after someone else&apos;s medications is a heavy responsibility. PillSafe keeps
              schedules visible and safety checks automatic, so caregivers can worry less.
            </p>
            <div className="mt-6 space-y-4">
              {CAREGIVER_SUPPORT.map(({ icon: Icon, title, desc }) => (
                <div key={title} className="flex items-start gap-3">
                  <div className="h-10 w-10 rounded-xl bg-blue-50 border border-blue-200 flex items-center justify-center shrink-0">
                    <Icon className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-900 text-sm">{title}</p>
                    <p className="text-sm text-slate-500 mt-0.5">{desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <Card className="bg-blue-50/50 border-blue-100">
            <div className="flex items-center gap-2 text-blue-700 font-semibold text-sm mb-4">
              <Users className="h-4 w-4" /> Who PillSafe is for
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-3">
                <Users className="h-5 w-5 text-teal-600 shrink-0" />
                <p className="text-sm text-slate-700">Elderly patients managing daily medications</p>
              </div>
              <div className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-3">
                <Heart className="h-5 w-5 text-teal-600 shrink-0" />
                <p className="text-sm text-slate-700">Caregivers supporting family members</p>
              </div>
              <div className="flex items-center gap-3 bg-white rounded-xl border border-slate-200 p-3">
                <Eye className="h-5 w-5 text-teal-600 shrink-0" />
                <p className="text-sm text-slate-700">Visually impaired users, via full voice support</p>
              </div>
            </div>
          </Card>
        </div>
      </section>

      {/* Accessibility-first design */}
      <section className="bg-white border-y border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-16">
          <div className="text-center max-w-2xl mx-auto mb-10">
            <h2 className="text-2xl sm:text-3xl font-bold text-slate-900">Accessibility-first design</h2>
            <p className="text-slate-500 mt-3">
              PillSafe is built so that literacy, eyesight, or language are never a barrier to
              understanding a medication.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {ACCESSIBILITY.map(({ icon: Icon, title, desc }) => (
              <Card key={title} className="text-center">
                <div className="h-12 w-12 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center mx-auto mb-3">
                  <Icon className="h-6 w-6 text-purple-600" />
                </div>
                <p className="font-semibold text-slate-900">{title}</p>
                <p className="text-sm text-slate-500 mt-1.5">{desc}</p>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="max-w-3xl mx-auto px-6 py-16 text-center">
        <ScanLine className="h-10 w-10 text-teal-600 mx-auto mb-4" />
        <h2 className="text-2xl font-bold text-slate-900">Ready to verify your medications?</h2>
        <p className="text-slate-500 mt-2">Create a free account and scan your first prescription in minutes.</p>
        <Link to={primaryCta.to} className="inline-flex items-center gap-2 mt-6 btn-primary !px-6 !py-3 min-h-[44px]">
          {isAuthenticated ? primaryCta.label : 'Create Free Account'} <ArrowRight className="h-4 w-4" />
        </Link>
      </section>
    </div>
  );
}
