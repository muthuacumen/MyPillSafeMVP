import { Link } from 'react-router-dom';
import { FlaskConical, ShieldCheck, MessageSquareWarning, ShieldOff, ExternalLink } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §5 -- transcribed verbatim. Layout/styling is ours; words are not.
//
// Phase 6 (Muthu's verification item 1): every citation whose DOI/venue was
// marked VERIFIED in the Phase 5 Grounding block of INTEGRATION_PLAN.md gets
// an outbound link (new tab, rel="noopener noreferrer"). MedSnap ID and
// Hanley & Lippman-Hand are deliberately left unlinked here -- they were not
// part of the closed VERIFIED set this phase's spec named, so no URL is
// invented for them (never guess a DOI).
const CITATIONS = [
  {
    title: 'Yaniv et al. — The NLM Pill Image Recognition Challenge',
    journal: 'IEEE AIPR 2016',
    url: 'https://doi.org/10.1109/AIPR.2016.8010584',
    point:
      'The founding evidence that open-set pill identification from consumer photos is unreliable: the challenge winner achieved only 43% top-5 accuracy. This is why MyPillSafe verifies against a personal profile instead of identifying against the full formulary.',
  },
  {
    title: 'Zeng, Cao & Zhang — MobileDeepPill',
    journal: 'ACM MobiSys 2017',
    url: 'https://doi.org/10.1145/3081333.3081336',
    point:
      'The NLM challenge winner, showing pill recognition can run on a phone — and that colour, shape, and imprint each carry complementary signal, the same attribute decomposition MyPillSafe uses.',
  },
  {
    title: 'Usuyama et al. — ePillID',
    journal: 'CVPR Workshops 2020',
    url: 'https://arxiv.org/abs/2005.14288',
    point:
      "Established the low-shot reality of pill recognition: most products have almost no training photos. MyPillSafe's text-attribute matching against Health Canada's registry avoids depending on per-pill image galleries.",
  },
  {
    title: 'Ling et al. — Few-Shot Pill Recognition',
    journal: 'CVPR 2020',
    url: 'https://doi.org/10.1109/CVPR42600.2020.00981',
    point:
      "Reinforces the few-shot framing with the CURE dataset and shows real-world capture conditions dominate difficulty — motivation for MyPillSafe's controlled capture card.",
  },
  {
    title: 'GO-PILL',
    journal: 'MDPI Mathematics 2025',
    url: 'https://www.mdpi.com/2227-7390/14/2/356',
    point:
      'Documents that low-contrast, debossed imprints are the hardest OCR case in pill imaging. Our own evaluation independently confirmed the imprint is the decisive, hardest attribute — MyPillSafe reads it twice with complementary methods and never trusts a single read.',
  },
  {
    title: 'MedSnap ID',
    journal: 'medRxiv 2020; related US patents',
    point:
      'Prior commercial art pairing a capture tray with a phone pill app — for medication authentication (counterfeit detection), not patient-profile verification. MyPillSafe cites it as prior art; our open, ablated capture-card design and verification-with-rejection task are the differences.',
  },
  {
    title: 'Hanley & Lippman-Hand',
    journal: 'JAMA 1983',
    point:
      '"If nothing goes wrong, is everything all right?" The rule of three: how we size our safety evaluations, so "no false accepts observed" comes with an honest statistical upper bound instead of a marketing claim.',
  },
  {
    title: 'CIHI — Drug Use Among Seniors in Canada',
    journal: 'Population evidence',
    url: 'https://www.cihi.ca/en/drug-use-among-seniors-in-canada',
    point:
      'The population evidence behind the problem statement: 1 in 4 Canadian seniors on 10+ drug classes; ~5× adverse-drug-reaction hospitalization risk at 10+ medications.',
  },
];

const PRINCIPLES = [
  {
    icon: ShieldCheck,
    title: 'Verify, don’t identify',
    desc: "the NLM challenge's 43% is the argument in one number.",
  },
  {
    icon: MessageSquareWarning,
    title: 'The AI that talks is never the AI that decides',
    desc: "deterministic matching and guards decide; the language model only phrases, strictly from cited sources, and is re-checked. Measurement forced this: a medication's name appears many times more often in other drugs' documents than in its own, so only deterministic scoping — not clever ranking — reliably prevents wrong-drug answers.",
  },
  {
    icon: ShieldOff,
    title: 'Abstention is a feature',
    desc: 'the system is tuned so a false "verified" is the rarest event, at the accepted cost of more "I\'m not sure" outcomes.',
  },
];

export default function SciencePage() {
  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">About</Link>
            <span>/</span>
            <span className="text-white/80">Scientific Foundation</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">About MyPillSafe</p>
          <h1 className="text-4xl font-bold">Scientific Foundation</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
            Every design decision in MyPillSafe traces to published evidence or to our own measured
            experiments — including the negative results.
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Section A -- published evidence */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <h2 className="text-xl font-bold text-navy mb-5">Published evidence MyPillSafe stands on</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {CITATIONS.map(({ title, journal, url, point }, i) => (
              <div key={title} className="bg-light border-l-4 border-teal-500 rounded-r-xl p-5">
                <div className="flex items-start gap-3">
                  <span className="flex-shrink-0 w-7 h-7 bg-navy/10 rounded-full text-xs flex items-center justify-center font-bold text-navy">
                    {i + 1}
                  </span>
                  <div>
                    {url ? (
                      <a
                        href={url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-navy text-sm mb-0.5 inline-flex items-center gap-1 hover:text-teal-700 hover:underline"
                      >
                        {title}
                        <ExternalLink className="h-3 w-3 shrink-0" />
                      </a>
                    ) : (
                      <p className="font-semibold text-navy text-sm mb-0.5">{title}</p>
                    )}
                    <p className="text-xs text-teal-700 mb-2 mt-0.5">{journal}</p>
                    <p className="text-xs text-slate-600 leading-relaxed">{point}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section B -- our own research (in preparation) */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4 flex-wrap">
            <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center shrink-0">
              <FlaskConical className="w-5 h-5 text-warning-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">Our own research</h2>
            <span className="inline-flex items-center bg-warning-bg text-warning-text border border-warning-border text-[11px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full">
              In Preparation
            </span>
          </div>

          <p className="text-xs font-semibold uppercase tracking-widest text-slate-400 mb-1">Working title</p>
          <p className="text-lg font-semibold text-navy italic mb-5 leading-snug">
            &ldquo;Verify, Don&apos;t Identify: Profile-Constrained Pill Verification from Consumer
            Photos with a Printed Capture Card.&rdquo;
          </p>

          <p className="text-slate-700 leading-relaxed mb-5">
            MyPillSafe&apos;s pill-vision pipeline is itself a research contribution in preparation.
            The paper formalizes verification-with-rejection against a patient&apos;s own medication
            profile as the right task for consumer pill safety; introduces a printed capture card
            that turns an uncontrolled phone photo into a calibrated one (white-balance patches,
            known geometry, forced flash); contributes a harmonized, human-adjudicated appearance
            reference for over 7,000 marketed Canadian DINs; and reports the negative results that
            shaped the system — most notably that on real phone photos, zero-shot models beat our
            fine-tuned ones on two of three vision heads, a caution for anyone trusting studio
            benchmarks.
          </p>

          <div className="bg-warning-bg border border-warning-border rounded-xl p-5">
            <p className="text-sm text-warning-text leading-relaxed">
              <strong>Status:</strong> in preparation. The design-phase experiments are complete; a
              pre-registered confirmatory capture study (the &ldquo;tray v2&rdquo; campaign — a pilot
              shoot followed by a 600-photo protocol with defined usability and safety endpoints) is
              still pending, and the paper will be drafted from those results. Until then,
              MyPillSafe&apos;s measured performance figures remain development-set diagnostics, and
              we deliberately do not quote them as product claims.
            </p>
          </div>
        </div>

        {/* Section C -- design principles */}
        <div className="bg-navy text-white rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-5">Design principles the evidence forced</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {PRINCIPLES.map(({ icon: Icon, title, desc }) => (
              <div key={title} className="bg-white/5 rounded-xl p-5">
                <Icon className="h-5 w-5 text-teal-300 mb-3" />
                <h3 className="font-bold text-white text-sm mb-2">{title}</h3>
                <p className="text-xs text-white/70 leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>
        </div>

        <AboutNav current="science" />
      </div>
    </div>
  );
}
