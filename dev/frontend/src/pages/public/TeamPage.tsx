import { Link } from 'react-router-dom';
import AboutNav from '@/components/AboutNav';

// Content pack §6 -- names/roles transcribed verbatim; task bullets are
// Phase 6 additions (Muthu's verification item 3), written to be at parity
// with PathoIntern's team page (role + concrete responsibility list). Task
// language only -- no fabricated metrics, credentials, or awards -- each
// bullet describes a real surface this app actually has.
const TEAM = [
  {
    initials: 'MJ',
    name: 'Muthuraj Jayakumar',
    role: 'Project Lead · ML Architecture',
    avatarBg: 'bg-navy',
    focus: [
      'Designed the five-brain architecture — prescription reading, pill vision, deterministic matching, monograph retrieval, and the cited answer voice.',
      'Set the verify / abstain / reject safety model, including why abstaining is treated as a correct outcome, not a failure.',
      'Directed the research grounding behind the pill-vision pipeline and its citation trail on the Scientific Foundation page.',
      'Wrote the disclaimer policy enforced on every decision-bearing screen: pill-scan results, Q&A answers, and DIN confirmations.',
    ],
  },
  {
    initials: 'SR',
    name: 'Sumanth Reddy',
    role: 'Backend & Systems Integration',
    avatarBg: 'bg-teal-600',
    focus: [
      'Built the FastAPI backend service layer — authentication, prescriptions, pill scans, and Q&A routes.',
      'Wired the brains sidecar service so the app can call pill-vision and matching over HTTP.',
      'Implemented DIN linking at prescription save: fuzzy-matching a scanned drug name, then requiring the patient to confirm before anything is committed.',
      'Maintained the automated backend test suite across every build.',
    ],
  },
  {
    initials: 'LR',
    name: 'Lohith Reddy',
    role: 'Frontend & User Experience',
    avatarBg: 'bg-burnt',
    focus: [
      'Built the dashboard, the pill-scan capture flow, and the Scan History views in React and Tailwind.',
      'Designed the verify / needs-a-closer-look / doesn’t-match result panel so each of the three outcomes reads distinctly at a glance.',
      'Implemented the mobile-first responsive layout, the bottom tab bar, and PWA installability.',
      'Built the public About / Vision / Problem / Scientific Foundation / Team pages and the project-explainer assistant widget.',
    ],
  },
  {
    initials: 'AO',
    name: 'Ali Ozdemir',
    role: 'Data Engineering · Reference Pipeline',
    avatarBg: 'bg-coral',
    focus: [
      'Built and harmonized the Canadian DIN appearance reference table the pill matcher checks scans against.',
      'Assembled the Health Canada product-monograph corpus behind the cited Q&A answers.',
      'Maintained the DIN reference-search endpoint used for one-tap suggestions at prescription save.',
      'Curated the evaluation photo sets used to test the matcher end-to-end before each build.',
    ],
  },
  {
    initials: 'AM',
    name: 'Abdullah Mohammed',
    role: 'Quality Assurance & Evaluation',
    avatarBg: 'bg-navy',
    focus: [
      'Ran the mandatory smoke tests and end-to-end verification pass on every build.',
      'Wrote and maintained the automated test suites covering prescriptions, pill scans, and Q&A.',
      'Verified English/French locale parity across the app’s user-facing copy.',
      'Documented deviations and bugs surfaced during verification passes, rather than letting them go unreported.',
    ],
  },
];

export default function TeamPage() {
  return (
    <div className="bg-light min-h-screen page-fade-in">
      <div className="bg-navy text-white py-16 px-4">
        <div className="max-w-5xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">Home</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">About</Link>
            <span>/</span>
            <span className="text-white/80">Team</span>
          </nav>
          <p className="text-coral font-semibold uppercase text-xs tracking-widest mb-2">About MyPillSafe</p>
          <h1 className="text-4xl font-bold">The Team</h1>
          <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
            A five-person capstone team at Conestoga College.
          </p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto py-12 px-4 space-y-8">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {TEAM.map(({ initials, name, role, avatarBg, focus }) => (
            <div key={name} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden card-hover">
              <div className="p-6 border-b border-slate-100">
                <div className="flex items-center gap-4">
                  <div className={`${avatarBg} text-white w-14 h-14 rounded-2xl flex items-center justify-center font-black text-lg flex-shrink-0`}>
                    {initials}
                  </div>
                  <div>
                    <h2 className="font-bold text-navy leading-tight">{name}</h2>
                    <p className="text-slate-500 text-sm">{role}</p>
                  </div>
                </div>
              </div>
              <div className="p-6">
                <h3 className="text-xs font-bold uppercase tracking-widest text-navy mb-3">Responsibilities</h3>
                <ul className="space-y-1.5">
                  {focus.map((f) => (
                    <li key={f} className="flex items-start gap-2 text-sm text-slate-600">
                      <span className="w-1.5 h-1.5 rounded-full bg-teal-500 mt-2 flex-shrink-0" />
                      {f}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          ))}
        </div>

        <p className="text-center text-sm text-slate-500 max-w-2xl mx-auto">
          MyPillSafe is a capstone project of the Conestoga College graduate program in AI &amp;
          Machine Learning.
        </p>

        <AboutNav current="team" />
      </div>
    </div>
  );
}
