import { Link } from 'react-router-dom';
import { AlertTriangle, Globe2, SearchX } from 'lucide-react';
import AboutNav from '@/components/AboutNav';

// Content pack §4 -- transcribed verbatim. Layout/styling is ours; words are not.

export default function ProblemPage() {
  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">About</Link>
            <span>/</span>
            <span className="text-white/80">Problem Statement</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">About MyPillSafe</p>
          <h1 className="text-4xl font-bold">The Problem</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
            Polypharmacy is normal, pills look alike, and medication information assumes you read
            English fluently.
          </p>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* Stat cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-navy text-white rounded-2xl p-6">
            <div className="text-4xl font-black mb-1">1 in 4</div>
            <p className="text-sm text-white/80 leading-relaxed">
              Canadian seniors is prescribed <strong>10 or more</strong> drug classes.
            </p>
            <p className="text-xs text-white/40 mt-3 italic">(CIHI, Drug Use Among Seniors in Canada)</p>
          </div>
          <div className="bg-coral text-white rounded-2xl p-6">
            <div className="text-4xl font-black mb-1">~5×</div>
            <p className="text-sm text-white/90 leading-relaxed">
              Seniors prescribed 10+ medications are about five times more likely to be hospitalized
              for an adverse drug reaction than seniors prescribed fewer.
            </p>
            <p className="text-xs text-white/60 mt-3 italic">(CIHI)</p>
          </div>
        </div>

        {/* The loose-pill moment */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-warning-bg flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-warning-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">The loose-pill moment</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The riskiest moment in home medication use is mundane: a pill out of its bottle. In a
            weekly organizer, on a counter, in a shared household — many tablets are small, white,
            and round, and look-alike pairs are common. For a senior managing ten medications,
            &ldquo;which pill is this?&rdquo; is a daily question with a non-trivial cost of getting
            it wrong.
          </p>
        </div>

        {/* Why "just identify the pill" fails */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-danger-bg flex items-center justify-center">
              <SearchX className="w-5 h-5 text-danger-text" />
            </div>
            <h2 className="text-xl font-bold text-navy">Why &ldquo;just identify the pill&rdquo; fails</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">
            The obvious answer — an app that identifies any pill from a photo — has been tried at
            research scale, and the results argue against it. In the U.S. National Library of
            Medicine&apos;s Pill Image Recognition Challenge, the winning system placed the correct
            pill in its top five candidates only 43% of the time on consumer photos. Against
            thousands of candidate products, that is not a safety tool. MyPillSafe&apos;s reframing:
            don&apos;t identify against everything — verify against the handful of medications{' '}
            <em>you actually take</em>, and refuse to guess beyond that.
          </p>
        </div>

        {/* Language barrier */}
        <div className="bg-white rounded-2xl shadow-sm p-8 border border-slate-100">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-teal-50 flex items-center justify-center">
              <Globe2 className="w-5 h-5 text-teal-600" />
            </div>
            <h2 className="text-xl font-bold text-navy">The language barrier</h2>
          </div>
          <p className="text-slate-700 leading-relaxed">
            Many Canadians manage medications in a language they did not grow up with. Monographs,
            labels, and pharmacy counselling largely assume English or French fluency. When
            comprehension drops, adherence and safety drop with it. MyPillSafe treats translation
            into the user&apos;s own language — grounded in the official monograph, never
            free-styled — as a first-class safety function.
          </p>
        </div>

        {/* Closing line */}
        <div className="bg-navy text-white rounded-2xl p-8 text-center">
          <p className="text-lg leading-relaxed">
            MyPillSafe exists for the moment a hand hesitates over an open pill organizer. Its job
            is to say &ldquo;yes, that&apos;s yours&rdquo;, &ldquo;no — stop&rdquo;, or &ldquo;I&apos;m
            not sure — check&rdquo;, and to be trustworthy in all three.
          </p>
        </div>

        <AboutNav current="problem" />
      </div>
    </div>
  );
}
