import { Link } from 'react-router-dom';
import { Trans, useTranslation } from 'react-i18next';
import { ArrowLeft, Camera, ShieldCheck, UserCheck, FileSearch } from 'lucide-react';
import { FIVE_BRAINS } from '@/content/fiveBrains';

/**
 * The first of five per-brain detail pages (FixbyOPUS3 Task A6 / §8).
 *
 * Deliberately structured as a REUSABLE TEMPLATE -- hero / what it does /
 * how it works / an optional measured section / back-to-About -- because
 * Pill Vision, Deterministic Matcher, Monograph Q&A and Cloud Voice get the
 * same treatment in later sessions.
 *
 * Two conventions this page follows on purpose:
 *
 *  1. OFF the About chain. It is reached from the About page's Five Brains
 *     card, not from `ABOUT_PAGES` -- see `content/fiveBrains.ts`.
 *  2. FULLY TRANSLATED (EN/FR). This SUPERSEDES the §0.7 English-only
 *     carve-out this page originally shipped with (Muthu's call
 *     2026-07-28). That carve-out existed for one stated reason -- the whole
 *     public About chain was hardcoded English, so translating one brain
 *     page would have dropped a French reader into French content one click
 *     from an English card and back to English after. The chain-wide FR gap
 *     was closed on 2026-07-29: `AboutPage`, `SciencePage`, `LandingPage`,
 *     `ProblemPage`, `VisionPage`, `TeamPage` and `ContactPage` are all on
 *     `t()` now, so the premise of the carve-out no longer holds and the
 *     page rejoins the rest of the chain.
 *
 * The numbers below are measured and re-runnable
 * (`documentation/evaluation/rx_parsing/`). They are counts, never
 * percentages-of-a-small-n, and this page must never claim "100% accuracy".
 * Their FRENCH rendering uses a space as the thousands separator (11 609),
 * which is the correct convention -- the values themselves are unchanged.
 */

const BRAIN = FIVE_BRAINS[0];

const HOW_IT_WORKS = [
  { key: 'read', icon: Camera },
  { key: 'propose', icon: FileSearch },
  { key: 'check', icon: ShieldCheck },
  { key: 'confirm', icon: UserCheck },
];

// The measured values are data, not language -- they stay identical in every
// locale (numeral form, so no English word leaks into FR). Only the system
// label and the note beneath it are translated.
//
// Source of truth: documentation/evaluation/rx_parsing/README.md §3 + §5 —
// the 2026-07-29 per-field widening, three runs per system, WORST run shown.
// The earlier, more flattering pre-widening numbers are preserved in that
// folder's `_prewidening` files; publishing them here was a red-team finding
// (2026-07-30) and must not regress. "Full labels" = every field of every
// medication correct; "Fields" = per-field score across all 24 labels (130).
const MEASURED_ROWS = [
  { key: 'regex', dev: '2/12', held: '1/12', fields: '94/130', events: '2' },
  { key: 'qwen', dev: '6/12', held: '9/12', fields: '120/130', events: '0' },
  { key: 'shipped', dev: '9/12', held: '11/12', fields: '125/130', events: '1†' },
  { key: 'haiku', dev: '12/12', held: '12/12', fields: '130/130', events: '0' },
];

const STILL_WRONG_KEYS = ['stillWrong1', 'stillWrong2', 'stillWrong3', 'stillWrong4'] as const;

export default function PrescriptionReaderPage() {
  const { t } = useTranslation();
  const Icon = BRAIN.icon;

  return (
    <div className="bg-light min-h-screen page-fade-in">
      {/* 1. Hero */}
      <div className="bg-navy text-white py-14 px-4">
        <div className="max-w-4xl mx-auto">
          <nav className="text-xs text-white/50 mb-3 flex flex-wrap items-center gap-2">
            <Link to="/" className="hover:text-white transition-colors">{t('common.home')}</Link>
            <span>/</span>
            <Link to="/about" className="hover:text-white transition-colors">{t('common.about')}</Link>
            <span>/</span>
            <span className="text-white/80">{t('public.brains.rxReader.breadcrumb')}</span>
          </nav>
          <div className="flex items-start gap-4">
            <div className="h-12 w-12 rounded-2xl bg-white/10 flex items-center justify-center shrink-0">
              <Icon className="h-6 w-6 text-white" />
            </div>
            <div className="min-w-0">
              <h1 className="text-3xl sm:text-4xl font-bold">{t(`public.fiveBrains.${BRAIN.key}.title`)}</h1>
              <p className="text-light/70 mt-3 max-w-2xl leading-relaxed">
                {t('public.brains.rxReader.heroLead', { desc: t(`public.fiveBrains.${BRAIN.key}.desc`) })}
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-4xl mx-auto py-12 px-4 space-y-6">
        {/* 2. What it does */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.rxReader.whatTitle')}</h2>
          <p className="text-slate-700 leading-relaxed">{t('public.brains.rxReader.whatBody1')}</p>
          <p className="text-slate-700 leading-relaxed mt-4">
            <Trans i18nKey="public.brains.rxReader.whatBody2" components={{ strong: <strong /> }} />
          </p>
        </div>

        {/* 3. How it works */}
        <div className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100">
          <h2 className="text-2xl font-bold text-navy mb-5">{t('public.brains.rxReader.howTitle')}</h2>
          <div className="space-y-4">
            {HOW_IT_WORKS.map(({ key, icon: StepIcon }) => (
              <div key={key} className="flex gap-4 items-start bg-light rounded-xl p-5">
                <div className="h-10 w-10 rounded-xl bg-navy/10 flex items-center justify-center shrink-0">
                  <StepIcon className="h-5 w-5 text-navy" />
                </div>
                <div className="min-w-0">
                  <h3 className="font-bold text-navy text-sm mb-1">{t(`public.brains.rxReader.how.${key}.title`)}</h3>
                  <p className="text-sm text-slate-600 leading-relaxed">{t(`public.brains.rxReader.how.${key}.body`)}</p>
                </div>
              </div>
            ))}
          </div>
          <div className="mt-5 rounded-xl border-l-4 border-teal-500 bg-light p-5">
            <p className="text-sm text-slate-700 leading-relaxed">
              <strong className="text-navy">{t('public.brains.rxReader.whyNoTimesTitle')}</strong>{' '}
              {t('public.brains.rxReader.whyNoTimesBody')}
            </p>
          </div>
        </div>

        {/* 4. Measured limitations */}
        <section
          id="rx-limitations"
          className="bg-white rounded-2xl shadow-sm p-6 sm:p-8 border border-slate-100 scroll-mt-24"
        >
          <h2 className="text-2xl font-bold text-navy mb-4">{t('public.brains.rxReader.limitationsTitle')}</h2>

          <p className="text-slate-700 leading-relaxed">{t('public.brains.rxReader.limitationsIntro')}</p>

          <h3 className="font-bold text-navy mt-6 mb-2">{t('public.brains.rxReader.readingTitle')}</h3>
          <p className="text-slate-700 leading-relaxed text-sm">
            <Trans i18nKey="public.brains.rxReader.readingBody" components={{ em: <em /> }} />
          </p>

          <h3 className="font-bold text-navy mt-6 mb-2">{t('public.brains.rxReader.turningTitle')}</h3>
          <p className="text-slate-700 leading-relaxed text-sm mb-4">{t('public.brains.rxReader.turningBody')}</p>

          <div className="overflow-x-auto -mx-6 px-6 sm:mx-0 sm:px-0">
            <table className="w-full text-sm border-collapse min-w-[34rem]">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2 pr-4 font-semibold">{t('public.brains.rxReader.table.approach')}</th>
                  <th className="py-2 pr-4 font-semibold">{t('public.brains.rxReader.table.own12')}</th>
                  <th className="py-2 pr-4 font-semibold">{t('public.brains.rxReader.table.unseen12')}</th>
                  <th className="py-2 pr-4 font-semibold">{t('public.brains.rxReader.table.fields')}</th>
                  <th className="py-2 font-semibold">{t('public.brains.rxReader.table.events')}</th>
                </tr>
              </thead>
              <tbody>
                {MEASURED_ROWS.map((row) => (
                  <tr key={row.key} className="border-t border-slate-100 align-top">
                    <td className="py-3 pr-4">
                      <span className="font-semibold text-navy">{t(`public.brains.rxReader.rows.${row.key}.system`)}</span>
                      <span className="block text-xs text-slate-500 mt-0.5">
                        {t(`public.brains.rxReader.rows.${row.key}.note`)}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-slate-700 whitespace-nowrap">{row.dev}</td>
                    <td className="py-3 pr-4 text-slate-700 whitespace-nowrap">{row.held}</td>
                    <td className="py-3 pr-4 text-slate-700 whitespace-nowrap">{row.fields}</td>
                    <td className="py-3 text-slate-700">{row.events}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs text-slate-500 leading-relaxed mt-3">{t('public.brains.rxReader.tableNote')}</p>
          <p className="text-xs text-slate-500 leading-relaxed mt-2">{t('public.brains.rxReader.tableFootnote')}</p>

          <h3 className="font-bold text-navy mt-6 mb-2">{t('public.brains.rxReader.notChosenTitle')}</h3>
          <p className="text-slate-700 leading-relaxed text-sm">{t('public.brains.rxReader.notChosenBody')}</p>

          <h3 className="font-bold text-navy mt-6 mb-2">{t('public.brains.rxReader.stillWrongTitle')}</h3>
          <ul className="text-slate-700 leading-relaxed text-sm space-y-2 list-disc pl-5">
            {STILL_WRONG_KEYS.map((key) => (
              <li key={key}>{t(`public.brains.rxReader.${key}`)}</li>
            ))}
          </ul>

          <p className="text-xs text-slate-500 leading-relaxed mt-5 border-t border-slate-100 pt-4">
            {t('public.brains.rxReader.repoNoteBefore')}
            <code className="mx-1 px-1.5 py-0.5 rounded bg-light text-slate-600 break-all">
              documentation/evaluation/rx_parsing/
            </code>
            {t('public.brains.rxReader.repoNoteAfter')}
          </p>
        </section>

        {/* 5. Back to About */}
        <div className="pt-2">
          <Link
            to="/about"
            className="inline-flex items-center justify-center gap-2 border border-navy text-navy py-3 px-6 rounded-xl font-semibold hover:bg-navy hover:text-white transition-colors min-h-[44px]"
          >
            <ArrowLeft className="h-4 w-4 flex-shrink-0" />
            {t('public.brains.backToAbout')}
          </Link>
        </div>
      </div>
    </div>
  );
}
