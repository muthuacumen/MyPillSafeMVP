import { useState } from 'react';
import { Link } from 'react-router-dom';
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
const STANDARD_DISCLAIMER = 'Decision support only — always confirm with your pharmacist or physician.';

function SafetyStrip({ text }: { text?: string | null }) {
  return (
    <div className="flex items-start gap-2 rounded-xl border border-slate-300 bg-slate-100 px-4 py-3 text-sm text-slate-700">
      <ShieldAlert className="h-4 w-4 shrink-0 mt-0.5 text-slate-500" />
      <span>{text || STANDARD_DISCLAIMER}</span>
    </div>
  );
}

/** Builds the "imprint matched exactly; colour and shape matched" sentence
 * from a candidate's per-attribute breakdown (SB2 CONTRACT.md §4 -- this
 * breakdown is mandatory to surface, not debug data). */
function describeBreakdown(b: PillCandidateBreakdown): string {
  let imprintPart: string;
  if (b.imprint_exact) {
    imprintPart = 'imprint matched exactly';
  } else if (b.ask_to_flip) {
    imprintPart = "imprint couldn't be read on this side";
  } else if (typeof b.imprint_fuzzy === 'number' && b.imprint_fuzzy > 0) {
    imprintPart = 'imprint matched closely';
  } else {
    imprintPart = "imprint couldn't be confirmed";
  }

  const colourOk = b.colour_score >= 0.75;
  const shapeOk = b.shape_score >= 0.99;
  let restPart: string;
  if (colourOk && shapeOk) restPart = 'colour and shape matched';
  else if (colourOk) restPart = 'colour matched, shape was uncertain';
  else if (shapeOk) restPart = 'shape matched, colour was uncertain';
  else restPart = 'colour and shape were uncertain';

  return `${imprintPart}; ${restPart}.`;
}

function CandidateHeadline({ candidate }: { candidate: PillRankedCandidate }) {
  return (
    <>
      <p className="font-semibold text-slate-900">
        {candidate.product ?? 'Unknown product'}
        {candidate.strength ? ` · ${candidate.strength}` : ''}
      </p>
      <p className="text-xs text-slate-500 mt-0.5">DIN {candidate.din}</p>
    </>
  );
}

function ShadowFusionHint({ show }: { show: boolean | undefined }) {
  if (!show) return null;
  return (
    <Alert
      variant="info"
      message="Image quality note: possible shadow interference — consider retaking on a flat, well-lit surface."
    />
  );
}

/** Renders the three SB2 decision states (verify/reject/abstain) as
 * first-class outcomes, plus the no-profile and not-detected states. Colour
 * semantics are binding: verify=green, reject=red, abstain=amber and NEVER
 * styled like reject (see documentation/integration/INTEGRATION_PLAN.md
 * Phase 3). */
export function PillResultPanel({ result, onRetake, onGoToPrescriptions }: PillResultPanelProps) {
  const [selectedDin, setSelectedDin] = useState<string | null>(null);

  if (result.status === 'no_profile') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Card className="text-center py-10">
          <div className="h-14 w-14 rounded-2xl bg-teal-50 border border-teal-200 flex items-center justify-center mx-auto mb-4">
            <Info className="h-7 w-7 text-teal-600" />
          </div>
          <p className="font-semibold text-slate-900">No confirmed medications yet</p>
          <p className="text-sm text-slate-500 mt-1.5 max-w-sm mx-auto">
            {result.message ??
              'Pill checking works against your confirmed medications. Scan a prescription and confirm its DIN, then come back here.'}
          </p>
          <Button className="mt-5" onClick={onGoToPrescriptions}>
            Scan a Prescription <ArrowRight className="h-4 w-4" />
          </Button>
        </Card>
      </div>
    );
  }

  const record = result.record;
  if (record && !record.detected) {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="warning" message="Couldn't find a pill in that photo." />
        <Card>
          <p className="text-sm font-semibold text-slate-900 mb-2">Tips for a clearer photo</p>
          <ul className="text-sm text-slate-600 space-y-1.5 list-disc list-inside">
            <li>Make sure the capture card is fully inside the frame</li>
            <li>Turn on your camera flash, or use bright, even lighting</li>
            <li>Place the pill on a flat surface, away from shadows</li>
            <li>Photograph one pill at a time</li>
          </ul>
        </Card>
        <SafetyStrip />
        <Button variant="secondary" onClick={onRetake}>
          <RefreshCw className="h-4 w-4" /> Try Again
        </Button>
      </div>
    );
  }

  const match = result.match;
  if (!match) return null;

  const disclaimer = <SafetyStrip text={match.disclaimer} />;

  if (match.decision === 'verify') {
    const top = match.ranked_candidates[0];
    return (
      <div className="space-y-4 animate-slide-up">
        <Card className="border-success-border bg-success-bg">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="h-6 w-6 text-success-text shrink-0" />
            <div className="flex-1">
              {top ? (
                <CandidateHeadline candidate={top} />
              ) : (
                <p className="font-semibold text-slate-900">DIN {match.matched_din}</p>
              )}
              {top && <p className="text-sm text-slate-700 mt-2">{describeBreakdown(top.breakdown)}</p>}
            </div>
          </div>
        </Card>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} />
        {match.matched_din && (
          <Link
            to={`/dashboard/qa?din=${encodeURIComponent(match.matched_din)}${
              top?.product ? `&name=${encodeURIComponent(top.product)}` : ''
            }`}
            className="inline-flex items-center gap-1.5 text-sm font-semibold text-teal-700 underline w-fit"
          >
            <MessageCircleQuestion className="h-4 w-4" /> Ask about this medication
          </Link>
        )}
        {disclaimer}
        <Button variant="secondary" onClick={onRetake}>
          Scan Another
        </Button>
      </div>
    );
  }

  if (match.decision === 'reject') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="error" message="This doesn't match any medication in your profile." />
        <div className="flex items-start gap-3 rounded-xl p-4 text-sm bg-danger-bg border border-danger-border text-danger-text">
          <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>If you were about to take this pill, stop and verify with a pharmacist before taking it.</span>
        </div>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} />
        {disclaimer}
        <Button variant="secondary" onClick={onRetake}>
          Scan Another
        </Button>
      </div>
    );
  }

  // abstain -- amber, never styled like reject.
  if (match.abstain_action === 'ask_to_flip') {
    return (
      <div className="space-y-4 animate-slide-up">
        <Alert variant="warning" message="We couldn't read a clear imprint on this side." />
        <Card>
          <p className="text-sm text-slate-700">
            Turn the pill over and photograph the other side so we can check its imprint.
          </p>
        </Card>
        <ShadowFusionHint show={record?.shadow_fusion_suspected} />
        {disclaimer}
        <Button onClick={onRetake}>
          <RefreshCw className="h-4 w-4" /> Photograph Other Side
        </Button>
      </div>
    );
  }

  // abstain / shortlist
  const shortlist = match.ranked_candidates.slice(0, 5);
  const selected = selectedDin ? shortlist.find((c) => c.din === selectedDin) : undefined;
  return (
    <div className="space-y-4 animate-slide-up">
      <Alert variant="warning" message="We're not fully certain — is it one of these?" />
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
            <CandidateHeadline candidate={c} />
          </button>
        ))}
      </div>

      {selected && (
        <Card className="border-warning-border bg-warning-bg">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-warning-text shrink-0" />
            <div>
              <CandidateHeadline candidate={selected} />
              <p className="text-sm text-slate-700 mt-2">{describeBreakdown(selected.breakdown)}</p>
              <p className="text-xs font-semibold text-warning-text mt-3">
                This is not a confirmed match — verify with a pharmacist before taking this pill.
              </p>
            </div>
          </div>
        </Card>
      )}

      <ShadowFusionHint show={record?.shadow_fusion_suspected} />
      {disclaimer}
      <Button variant="secondary" onClick={onRetake}>
        Scan Another
      </Button>
    </div>
  );
}
