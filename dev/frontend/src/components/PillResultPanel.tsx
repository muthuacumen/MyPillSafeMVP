import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Info,
  MessageCircleQuestion,
  RefreshCw,
  ShieldAlert,
  XCircle,
} from 'lucide-react';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Alert } from '@/components/ui/Alert';
import type { PillAnalysisV2Response, PillCandidateBreakdown, PillRankedCandidate } from '@/types';

interface PillResultPanelProps {
  result: PillAnalysisV2Response;
  /** Returns to the capture step (re-take / scan another / photograph the
   * other side -- all the same underlying action). */
  onRetake: () => void;
  onGoToPrescriptions: () => void;
}

// Phase 6 safety audit (PisaPillsafeFindings.md §5/§7): the result screen is
// the moment of highest risk, and the only safety framing here used to be a
// skippable text-xs caption. This strip is a SCOPED EXCEPTION to this file's
// normal zero-diff rule (binding rule 1) -- it may only add this persistent,
// non-dismissible, identically-styled strip to every result state; decision
// colour tokens and all existing state logic/rendering are untouched.
//
// FixbySonnet1 Task 7: every string literal below was extracted to an i18n
// key (`pillResult.*`, i18n/locales/{en,fr}.json) -- non-negotiable #3 still
// applies, so this was a byte-for-byte copy swap only: no decision-state
// logic, colour token, or JSX structure changed.
function SafetyStrip({ text, t }: { text?: string | null; t: TFunction }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-slate-300 bg-slate-100 px-4 py-3 text-sm text-slate-700">
      <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-slate-500" />
      <span>{text || t('pillResult.disclaimerDefault')}</span>
    </div>
  );
}

/** Builds the "imprint matched exactly; colour and shape matched" sentence
 * from a candidate's per-attribute breakdown (SB2 CONTRACT.md §4 -- this
 * breakdown is mandatory to surface, not debug data). */
function describeBreakdown(t: TFunction, b: PillCandidateBreakdown): string {
  let imprintPart: string;
  if (b.imprint_exact) {
    imprintPart = t('pillResult.breakdown.imprintExact');
  } else if (b.ask_to_flip) {
    imprintPart = t('pillResult.breakdown.imprintAskToFlip');
  } else if (typeof b.imprint_fuzzy === 'number' && b.imprint_fuzzy > 0) {
    imprintPart = t('pillResult.breakdown.imprintFuzzy');
  } else {
    imprintPart = t('pillResult.breakdown.imprintUnconfirmed');
  }

  const colourOk = b.colour_score >= 0.75;
  const shapeOk = b.shape_score >= 0.99;
  let restPart: string;
  if (colourOk && shapeOk) restPart = t('pillResult.breakdown.colourAndShapeMatched');
  else if (colourOk) restPart = t('pillResult.breakdown.colourMatchedShapeUncertain');
  else if (shapeOk) restPart = t('pillResult.breakdown.shapeMatchedColourUncertain');
  else restPart = t('pillResult.breakdown.colourAndShapeUncertain');

  return `${imprintPart}; ${restPart}.`;
}

function CandidateHeadline({ candidate, t }: { candidate: PillRankedCandidate; t: TFunction }) {
  return (
    <>
      <p className="font-semibold text-slate-900">
        {candidate.product ?? t('pillResult.unknownProduct')}
        {candidate.strength ? ` · ${candidate.strength}` : ''}
      </p>
      <p className="text-xs text-slate-500 mt-0.5">DIN {candidate.din}</p>
    </>
  );
}

function ShadowFusionHint({ show, t }: { show: boolean | undefined; t: TFunction }) {
  if (!show) return null;
  return <Alert variant="info" message={t('pillResult.shadowFusionHint')} />;
}

/** Renders the three SB2 decision states (verify/reject/abstain) as
 * first-class outcomes, plus the no-profile and not-detected states. Colour
 * semantics are binding: verify=green, reject=red, abstain=amber and NEVER
 * styled like reject (see documentation/integration/INTEGRATION_PLAN.md
 * Phase 3). */
export function PillResultPanel({ result, onRetake, onGoToPrescriptions }: PillResultPanelProps) {
  const { t } = useTranslation();
  const [selectedDin, setSelectedDin] = useState<string | null>(null);

  if (result.status === 'no_profile') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Card className="text-center py-10">
          <div className="h-14 w-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
            <Info className="h-7 w-7 text-teal-600" />
          </div>
          <p className="font-semibold text-slate-900">{t('pillResult.noProfile.title')}</p>
          <p className="text-sm text-slate-500 mt-1.5 max-w-sm mx-auto">
            {result.message ?? t('pillResult.noProfile.defaultMessage')}
          </p>
          <Button className="mt-5" onClick={onGoToPrescriptions}>
            {t('pillResult.noProfile.cta')} <ArrowRight className="h-4 w-4" />
          </Button>
        </Card>
      </div>
    );
  }

  const record = result.record;
  if (record && !record.detected) {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="warning" message={t('pillResult.notDetected.alert')} />
        <Card>
          <p className="text-sm font-semibold text-slate-900 mb-2">{t('pillResult.notDetected.tipsTitle')}</p>
          <ul className="text-sm text-slate-600 space-y-1.5 list-disc list-inside">
            <li>{t('pillResult.notDetected.tip1')}</li>
            <li>{t('pillResult.notDetected.tip2')}</li>
            <li>{t('pillResult.notDetected.tip3')}</li>
            <li>{t('pillResult.notDetected.tip4')}</li>
          </ul>
        </Card>
        <SafetyStrip t={t} />
        <Button variant="secondary" onClick={onRetake}>
          <RefreshCw className="h-4 w-4" /> {t('pillResult.notDetected.tryAgain')}
        </Button>
      </div>
    );
  }

  const match = result.match;
  if (!match) return null;

  const disclaimer = <SafetyStrip text={match.disclaimer} t={t} />;

  if (match.decision === 'verify') {
    const top = match.ranked_candidates[0];
    return (
      <div className="space-y-4 animate-slide-up">
        <Card className="border-success-border bg-success-bg">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-6 w-6 text-success-text shrink-0" />
            <div className="flex-1">
              {top ? (
                <CandidateHeadline candidate={top} t={t} />
              ) : (
                <p className="font-semibold text-slate-900">DIN {match.matched_din}</p>
              )}
              {top && <p className="text-sm text-slate-700 mt-2">{describeBreakdown(t, top.breakdown)}</p>}
            </div>
          </div>
        </Card>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} t={t} />
        {match.matched_din && (
          <Link
            to={`/dashboard/qa?din=${encodeURIComponent(match.matched_din)}${
              top?.product ? `&name=${encodeURIComponent(top.product)}` : ''
            }`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 underline w-fit"
          >
            <MessageCircleQuestion className="h-4 w-4" /> {t('pillResult.verify.askAboutMedication')}
          </Link>
        )}
        {disclaimer}
        <Button variant="secondary" onClick={onRetake}>
          {t('pillResult.scanAnother')}
        </Button>
      </div>
    );
  }

  if (match.decision === 'reject') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="error" message={t('pillResult.reject.alert')} />
        <div className="flex items-start gap-3 rounded-xl p-4 text-sm bg-danger-bg border border-danger-border text-danger-text">
          <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{t('pillResult.reject.warning')}</span>
        </div>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} t={t} />
        {disclaimer}
        <Button variant="secondary" onClick={onRetake}>
          {t('pillResult.scanAnother')}
        </Button>
      </div>
    );
  }

  // abstain -- amber, never styled like reject.
  if (match.abstain_action === 'ask_to_flip') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="warning" message={t('pillResult.askToFlip.alert')} />
        <Card>
          <p className="text-sm text-slate-700">{t('pillResult.askToFlip.instructions')}</p>
        </Card>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} t={t} />
        {disclaimer}
        <Button onClick={onRetake}>
          <RefreshCw className="h-4 w-4" /> {t('pillResult.askToFlip.cta')}
        </Button>
      </div>
    );
  }

  // abstain / shortlist
  const shortlist = match.ranked_candidates.slice(0, 5);
  const selected = selectedDin ? shortlist.find((c) => c.din === selectedDin) : undefined;
  return (
    <div className="space-y-4 animate-slide-up">
      <Alert variant="warning" message={t('pillResult.shortlist.alert')} />
      <div className="space-y-2">
        {shortlist.map((c) => (
          <button
            key={c.din}
            type="button"
            onClick={() => setSelectedDin((prev) => (prev === c.din ? null : c.din))}
            aria-pressed={selectedDin === c.din}
            className={`w-full text-left rounded-xl border p-3 transition-colors ${
              selectedDin === c.din
                ? 'border-warning-border bg-warning-bg'
                : 'border-slate-200 bg-white hover:border-teal-300'
            }`}
          >
            <CandidateHeadline candidate={c} t={t} />
          </button>
        ))}
      </div>

      {selected && (
        <Card className="border-warning-border bg-warning-bg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning-text shrink-0" />
            <div>
              <CandidateHeadline candidate={selected} t={t} />
              <p className="text-sm text-slate-700 mt-2">{describeBreakdown(t, selected.breakdown)}</p>
              <p className="text-xs font-semibold text-warning-text mt-3">
                {t('pillResult.shortlist.notConfirmed')}
              </p>
            </div>
          </div>
        </Card>
      )}

      <ShadowFusionHint show={record?.shadow_fusion_suspected} t={t} />
      {disclaimer}
      <Button variant="secondary" onClick={onRetake}>
        {t('pillResult.scanAnother')}
      </Button>
    </div>
  );
}
