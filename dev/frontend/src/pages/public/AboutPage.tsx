import { Link } from 'react-router-dom';
import { ScanLine, Eye, Scale, BookOpen, Cloud, Ruler, ClipboardCheck, BarChart3, TestTube2 } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §2 -- transcribed verbatim. Layout/styling is ours; words are not.

const FIVE_BRAINS = [
  {
    icon: ScanLine,
    title: 'Prescription Reader (OCR)',
    desc: 'reads the prescription image, extracts medications and schedule, and proposes Health Canada DIN matches that the user confirms — never auto-committed.',
  },
  {
    icon: Eye,
    title: 'Pill Vision',
    desc: "isolates the pill on the capture card and reads its colour (calibrated against the card's printed patches), shape, and imprint. The imprint is read twice by complementary methods.",
  },
  {
    icon: Scale,
    title: 'Deterministic Matcher',
    desc: 'a transparent, formula-based scorer (deliberately not machine learning) that compares the pill’s attributes against the user’s confirmed medications and returns exactly one of: verify, abstain, or reject. Its thresholds are tuned to make false accepts the rarest event.',
  },
  {
    icon: BookOpen,
    title: 'Monograph Retrieval',
    desc: 'finds the relevant, DIN-scoped passages of Health Canada product monographs, with deterministic safety guards — including a hard refusal to answer dosing questions.',
  },
  {
    icon: Cloud,
    title: 'Answer Voice (cloud AI)',
    desc: "the only cloud component. It phrases the final answer in the user's language, strictly from the retrieved cited passages, and its answers are re-checked by the same deterministic guards.",
  },
];

const HOW_WE_WORKED = [
  {
    icon: Ruler,
    title: 'Measure the assumption before building on it.',
    desc: "The project's first reference dataset was rebuilt from scratch after a check revealed it described products that were approved in Canada but never actually sold — pills no patient could possess.",
  },
  {
    icon: ClipboardCheck,
    title: 'Pre-register the bar, then report honestly.',
    desc: 'Every evaluation had its pass/fail criteria written down before the run. Some runs failed their gates; the failures are documented, not reframed.',
  },
  {
    icon: BarChart3,
    title: 'Let the data decide.',
    desc: 'Candidate models competed against simple zero-shot baselines — and on real phone photos, the baselines won two of three vision components. The trained models that looked better on studio benchmarks shipped only where they earned it.',
  },
  {
    icon: TestTube2,
    title: 'Test everything.',
    desc: "A mandatory smoke test or spot-check ran on every build of the project — and every single one caught at least one real bug. The deterministic safety guards have a combined zero failures across all evaluation rounds; every incident came from the model-judgment layer, which is exactly why models don't make the decisions.",
  },
];

export default function AboutPage() {
  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <span className="text-white/80">About</span>
          </nav>
          <h1 className="text-4xl font-bold">About MyPillSafe</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
            A medication-safety assistant built as five cooperating brains — each one doing the job
            the evidence says it can actually do.
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* What MyPillSafe Is */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">What MyPillSafe Is</h2>
          <p className="text-slate-700 leading-relaxed">
            MyPillSafe helps two groups the medication system underserves: seniors managing many
            medications, and Canadians who read medical information more comfortably in a language
            other than English or French. It turns a prescription into a personal medication
            profile, verifies loose pills by photo against that profile, and answers medication
            questions from Health Canada product monographs — with citations, in the user&apos;s
            language.
          </p>
        </div>

        {/* Five Brains */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-5">The Five Brains</h2>
          <div className="space-y-4">
            {FIVE_BRAINS.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="flex gap-4 items-start bg-light rounded-xl p-5">
                <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
                  <Icon className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h3 className="font-bold text-navy text-sm mb-1">{title}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Why this architecture */}
        <div className="bg-navy text-white rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-3">Why this architecture</h2>
          <p className="text-white/75 leading-relaxed">
            The split is deliberate: everything that decides is deterministic and auditable; the AI
            that talks is never the AI that decides. That separation came from measurement, not
            taste — during evaluation, a smaller language model answered a safety-critical allergy
            question incorrectly <em>against its own retrieved source</em>. The architecture makes
            that class of failure detectable and containable.
          </p>
        </div>

        {/* How we worked */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">How we worked</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {HOW_WE_WORKED.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-light rounded-xl p-5 border-l-4 border-teal-500">
                <Icon className="h-5 w-5 text-teal-600 mb-2" />
                <h3 className="font-bold text-navy text-sm mb-1.5">{title}</h3>
                <p className="text-xs text-slate-600 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Scope note */}
        <div className="bg-light border border-slate-200 rounded-2xl p-6 text-center">
          <p className="text-sm text-slate-600">
            MyPillSafe is a Conestoga College capstone project, built for Canada (DIN-based, Health
            Canada monographs). It is decision-support only.
          </p>
        </div>

        <AboutNav current="about" />
      </div>
    </div>
  );
}
