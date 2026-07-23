import { Link } from 'react-router-dom';
import { ShieldCheck, Eye, Compass, Languages, HeartHandshake } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §3 -- transcribed verbatim. Layout/styling is ours; words are not.

const VALUES = [
  {
    icon: ShieldCheck,
    title: 'Safety before convenience',
    desc: 'When evidence is thin, MyPillSafe abstains. An honest "I\'m not sure — check with your pharmacist" beats a confident guess every time.',
    color: 'border-warning-border text-warning-text',
  },
  {
    icon: Eye,
    title: 'Evidence before features',
    desc: 'Every component earned its place through measurement. Features that failed evaluation were removed, not shipped.',
    color: 'border-teal-300 text-teal-700',
  },
  {
    icon: Languages,
    title: 'Language is a safety feature',
    desc: "Medication information you can't fully understand is a risk factor. Answering in the user's own language is core to the mission, not a nice-to-have.",
    color: 'border-navy/30 text-navy',
  },
  {
    icon: HeartHandshake,
    title: 'Honesty about limits',
    desc: 'MyPillSafe is research-grade decision support with mandatory disclaimers, not a medical device. It says so on every screen.',
    color: 'border-coral/30 text-coral',
  },
];

export default function VisionPage() {
  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">About</Link>
            <span>/</span>
            <span className="text-white/80">Vision &amp; Mission</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">About MyPillSafe</p>
          <h1 className="text-4xl font-bold">Vision &amp; Mission</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Mission (hero statement) */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-navy/10 flex items-center justify-center">
              <Compass className="w-5 h-5 text-navy" />
            </div>
            <h2 className="text-2xl font-bold text-navy">Mission</h2>
          </div>
          <blockquote className="text-xl sm:text-2xl text-navy font-semibold italic border-l-4 border-coral pl-5 leading-relaxed">
            To help seniors and Canadians with language barriers take the right medication at the
            right time — by verifying what&apos;s in their hand, warning when something is wrong,
            and explaining in the language they think in.
          </blockquote>
        </div>

        {/* Vision */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-5">
            <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
              <Eye className="w-5 h-5 text-teal-600" />
            </div>
            <h2 className="text-2xl font-bold text-navy">Vision</h2>
          </div>
          <p className="text-slate-700 leading-relaxed text-lg">
            A Canada where a language barrier or a crowded pill organizer never turns into a
            medication error — where every household has a safety layer that is honest about what
            it knows and what it doesn&apos;t.
          </p>
        </div>

        {/* Values */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">Values</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {VALUES.map(({ icon: Icon, title, desc, color }) => (
              <div key={title} className={`bg-light rounded-xl p-5 border-l-4 ${color.split(' ')[0]}`}>
                <Icon className={`h-5 w-5 mb-2 ${color.split(' ')[1]}`} />
                <h3 className="font-bold text-navy text-sm mb-1.5">{title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        <AboutNav current="vision" />
      </div>
    </div>
  );
}
