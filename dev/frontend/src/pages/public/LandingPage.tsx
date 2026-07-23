import { Link } from 'react-router-dom';
import {
  ScanLine, CheckCircle2, Languages, ArrowRight,
  AlertTriangle, XCircle, SearchX, ShieldCheck,
} from 'lucide-react';
import { Logo } from '@/components/ui/Logo';

// Content pack §1 -- transcribed verbatim. Layout/styling is ours; words are not.

const HOW_IT_WORKS = [
  {
    step: '01',
    title: 'Scan Your Prescription',
    desc: 'Photograph your prescription. MyPillSafe reads the medications and schedule and builds your personal medication profile.',
    icon: ScanLine,
  },
  {
    step: '02',
    title: 'Confirm Your Medications',
    desc: "Each medication is matched against Health Canada's Drug Identification Numbers (DINs). You confirm with one tap — MyPillSafe never guesses on your behalf.",
    icon: CheckCircle2,
  },
  {
    step: '03',
    title: 'Verify a Pill',
    desc: 'Photograph a loose pill on the MyPillSafe capture card. Its colour, shape, and imprint are checked against your profile — not the whole formulary.',
    icon: ShieldCheck,
  },
  {
    step: '04',
    title: 'Ask in Your Language',
    desc: 'Ask questions about your medications. Answers come only from Health Canada product monographs, with citations, in the language you choose.',
    icon: Languages,
  },
];

const OUTCOMES = [
  {
    label: 'Verified',
    colour: 'green',
    icon: CheckCircle2,
    desc: "This pill matches a medication in your profile. You'll see exactly which attributes matched.",
    classes: 'bg-success-bg border-success-border text-success-text',
  },
  {
    label: 'Needs a Closer Look',
    colour: 'amber',
    icon: AlertTriangle,
    desc: 'MyPillSafe isn’t sure yet. It may ask you to flip the pill and photograph the other side, or show you a short list to confirm.',
    classes: 'bg-warning-bg border-warning-border text-warning-text',
  },
  {
    label: "Doesn't Match",
    colour: 'red',
    icon: XCircle,
    desc: "This pill doesn't match anything in your profile. A clear warning, because a stray pill is exactly what MyPillSafe exists to catch.",
    classes: 'bg-danger-bg border-danger-border text-danger-text',
  },
  {
    label: 'Nothing Detected',
    colour: 'navy',
    icon: SearchX,
    desc: 'No pill found in the photo, with capture tips to try again.',
    classes: 'bg-navy/5 border-navy/20 text-navy',
  },
];

const SCIENCE_STRIP = [
  {
    title: 'NLM Pill Image Recognition Challenge (2016)',
    journal: 'IEEE AIPR',
    point:
      'Even the winning system found the right pill among its top five guesses only 43% of the time. Open-set pill identification is the wrong task for a safety app — so MyPillSafe verifies against your profile instead.',
  },
  {
    title: 'ePillID (Usuyama et al., 2020)',
    journal: 'CVPR Workshops',
    point:
      "The benchmark for fine-grained pill recognition with few examples per pill: most medications have almost no photos to learn from. MyPillSafe's attribute-based design avoids depending on per-pill image galleries.",
  },
  {
    title: 'GO-PILL (2025)',
    journal: 'MDPI Mathematics',
    point:
      'Reading the tiny imprint pressed into a pill is the hardest and most decisive step. MyPillSafe reads every imprint twice, with two complementary methods, before trusting it.',
  },
  {
    title: 'CIHI — Drug Use Among Seniors in Canada',
    journal: 'Population evidence',
    point:
      '1 in 4 Canadian seniors is prescribed 10 or more drug classes, and seniors on 10+ medications are about five times more likely to be hospitalized for an adverse drug reaction.',
  },
];

export default function LandingPage() {
  return (
    <div className="page-fade-in">
      {/* ── Hero ── */}
      <section className="relative overflow-hidden bg-brand-hero text-white">
        <div className="absolute -right-24 -top-24 h-80 w-80 rounded-full bg-white/5" />
        <div className="absolute -left-16 bottom-0 h-64 w-64 rounded-full bg-white/5" />
        <div className="relative max-w-6xl mx-auto px-6 py-20 lg:py-28">
          <div className="flex flex-col lg:flex-row items-center gap-12 lg:gap-16">
            <div className="flex-1 text-center lg:text-left">
              <span className="inline-flex items-center gap-2 bg-white/10 border border-white/20 rounded-full px-4 py-1.5 text-xs font-semibold uppercase tracking-widest text-white/90">
                Capstone MVP · Decision-Support Only
              </span>
              <h1 className="text-4xl sm:text-5xl font-extrabold leading-tight mt-6 tracking-tight">
                The wrong pill should never go unnoticed.
              </h1>
              <p className="mt-5 text-light/80 max-w-xl mx-auto lg:mx-0 text-lg leading-relaxed">
                MyPillSafe is a medication-safety assistant for seniors and Canadians with language
                barriers. It reads your prescription, verifies your pills from a photo, and answers
                medication questions in your language — and when it isn&apos;t sure, it says so.
              </p>
              <div className="mt-8 flex flex-wrap items-center justify-center lg:justify-start gap-4">
                <Link
                  to="/register"
                  className="inline-flex items-center gap-2 bg-coral hover:bg-coral/90 text-white px-6 py-3 rounded-xl font-semibold transition-colors shadow-lg min-h-[44px]"
                >
                  Get Started <ArrowRight className="h-4 w-4" />
                </Link>
                <Link
                  to="/about"
                  className="inline-flex items-center gap-2 bg-white/10 border border-white/30 text-white px-6 py-3 rounded-xl font-semibold hover:bg-white/20 transition-colors min-h-[44px]"
                >
                  Learn More
                </Link>
              </div>
            </div>

            {/* White logo panel -- BINDING dark-surface rule: navy linework
                must never sit directly on this navy hero. */}
            <div className="flex-shrink-0 flex justify-center">
              <div className="bg-white rounded-3xl p-8 w-64 sm:w-72 shadow-[0_0_60px_rgba(255,255,255,0.12)]">
                <Logo className="h-auto w-full" />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How MyPillSafe Works ── */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-navy text-center mb-2">How MyPillSafe Works</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mt-10">
            {HOW_IT_WORKS.map(({ step, title, desc, icon: Icon }) => (
              <div key={step} className="bg-light rounded-2xl p-6 border-t-4 border-teal-500 card-hover">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-3xl font-black text-teal-600">{step}</span>
                  <Icon className="h-6 w-6 text-navy" />
                </div>
                <h3 className="font-bold text-navy mb-2">{title}</h3>
                <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Three-Outcome Safety Design ── */}
      <section className="py-20 px-4 bg-light">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-navy text-center mb-3">The Three-Outcome Safety Design</h2>
          <p className="text-slate-600 text-center max-w-2xl mx-auto mb-10 leading-relaxed">
            Every pill check ends in one of three honest outcomes. When MyPillSafe isn&apos;t sure,
            abstaining is the design — not a failure.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
            {OUTCOMES.map(({ label, icon: Icon, desc, classes }) => (
              <div key={label} className={`rounded-2xl border p-6 ${classes}`}>
                <Icon className="h-7 w-7 mb-3" />
                <p className="font-bold mb-2">{label}</p>
                <p className="text-sm leading-relaxed opacity-90">{desc}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-sm text-slate-500 mt-8 max-w-2xl mx-auto leading-relaxed">
            MyPillSafe is tuned so that a wrong pill being called &ldquo;verified&rdquo; is the rarest
            possible event — even at the cost of asking you to try again more often.
          </p>

          {/* Why verify instead of identify? */}
          <div className="max-w-3xl mx-auto mt-12 bg-navy text-white rounded-2xl p-8">
            <h3 className="text-xl font-bold mb-3">Why verify instead of identify?</h3>
            <p className="text-white/75 leading-relaxed">
              Because Canadian pills genuinely collide. In building our reference data we found more
              than a dozen different products that are all the same &ldquo;blue diamond tablet, SIL
              25&rdquo; — cross-licensed generics no camera could ever tell apart. Against the whole
              formulary, that problem is unsolvable; against the handful of medications{' '}
              <em>you</em> actually take, it is tractable. That reframing — verify, don&apos;t identify
              — is the project&apos;s core idea.
            </p>
          </div>
        </div>
      </section>

      {/* ── Scientific Foundation strip ── */}
      <section className="py-20 px-4 bg-navy text-white">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-2">
            <Link to="/about/science" className="hover:text-light/80 transition-colors">
              Scientific Foundation
            </Link>
          </h2>
          <p className="text-light/60 text-center mb-10 max-w-2xl mx-auto text-sm">
            MyPillSafe&apos;s design decisions rest on peer-reviewed evidence — including the evidence
            that told us what NOT to build.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {SCIENCE_STRIP.map(({ title, journal, point }, i) => (
              <div key={title} className="bg-white/5 border-l-4 border-teal-500 rounded-r-xl p-5">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 bg-white/10 rounded-full text-xs flex items-center justify-center font-bold text-white">
                    {i + 1}
                  </span>
                  <div>
                    <p className="font-semibold text-white text-sm mb-0.5">{title}</p>
                    <p className="text-xs text-teal-300 mb-2">{journal}</p>
                    <p className="text-xs text-white/70 leading-relaxed">{point}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
          <div className="text-center mt-8">
            <Link
              to="/about/science"
              className="inline-flex items-center gap-2 text-sm font-semibold text-teal-300 hover:text-white transition-colors"
            >
              Read the full Scientific Foundation <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </section>

      {/* ── Closing CTA ── */}
      <section className="py-20 px-4 bg-white">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-navy mb-4">
            Built to warn, designed to abstain, never to guess.
          </h2>
          <p className="text-slate-600 mb-8 leading-relaxed">
            MyPillSafe is a capstone research project. It supports your decisions — it does not make
            them. Every screen carries the same rule: verify with your pharmacist.
          </p>
          <Link
            to="/about/vision"
            className="inline-flex items-center gap-2 bg-navy hover:bg-primary-dark text-white px-8 py-3 rounded-xl font-semibold transition-colors min-h-[44px]"
          >
            Read the Vision <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </div>
  );
}
