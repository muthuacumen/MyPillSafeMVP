export interface User {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  first_name: string | null;
  last_name: string | null;
  medications_analyzed: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface PillInfo {
  pill_id: string;
  name: string;
  confidence: number;
  color: string;
  shape: string;
  imprint: string | null;
}

export interface LabelInfo {
  drug_name: string | null;
  dosage: string | null;
  frequency: string | null;
  refills_remaining: number | null;
  expiry_date: string | null;
}

export interface AnalyzeResult {
  request_id: string;
  status: string;
  pills_detected: PillInfo[];
  label: LabelInfo;
  guidance: string;
  safety_alerts: string[];
  ml_pipeline_enabled: boolean;
}

export type TimeSlot = 'morning' | 'afternoon' | 'evening' | 'night';

export interface Prescription {
  id: string;
  drug_name: string;
  dosage: string | null;
  frequency_text: string | null;
  frequency_type: string | null;
  time_slots: TimeSlot[];
  specific_times: string[];
  with_food: boolean;
  purpose: string | null;
  max_daily_dose: number | null;
  prescribing_doctor: string | null;
  refills_remaining: number | null;
  expiry_date: string | null;
  is_active: boolean;
  image_path: string | null;
  /** Canonical 8-digit zero-padded Health Canada DIN, e.g. "00013803". */
  din: string | null;
  din_confirmed: boolean;
  /** Task B3: whether a photo can verify this medication at all. `null`
   * means it could not be established -- render nothing, never a guess. */
  pill_verifiable: boolean | null;
  created_at: string;
  updated_at: string;

  /* --- Review workflow (FixbyOPUS3). A scanned medication is a PROPOSAL
   * until the patient approves it: nothing auto-commits a drug name, DIN or
   * schedule, and no reminder fires for a pending row. */
  review_status: ReviewStatus;
  /** Which proposer produced this row -- 'qwen' (local LLM) or 'regex'. */
  parse_source: string | null;
  /** Deterministic guardrail flags raised at parse time. */
  parse_flags: ParseFlag[];
}

export type ReviewStatus = 'pending' | 'approved';

/** Guardrail flags (backend `app/services/rx_guardrails.py`).
 * `not_on_label` and `needs_schedule` BLOCK approval until the user edits or
 * explicitly confirms the field; the rest are informational.
 *
 * `as_needed` (G6) is informational because it EXPLAINS the `needs_schedule`
 * that always accompanies it — the label said "as needed", so no reminder
 * time was derived. Two acknowledgements for one fact would be noise. */
export type ParseFlag =
  | 'not_in_reference'
  | 'not_on_label'
  | 'needs_schedule'
  | 'conflict'
  | 'as_needed';

export const BLOCKING_PARSE_FLAGS: ParseFlag[] = ['not_on_label', 'needs_schedule'];

/** How well a candidate's product name covers the words the LABEL printed
 * (backend `app/services/lasa.py`).
 * - `exact`        — keeps every word the label printed; safe to one-tap.
 * - `manufacturer` — only a generic-manufacturer prefix differs (APO vs
 *   TEVA): a real difference, because the pill looks different and SB2
 *   matches on appearance, but not a wrong-medicine risk.
 * - `look_alike`   — dropped a real word from the label. ZOLTIRAX→ZOVIRAX,
 *   TYLENOL PM→TYLENOL EXTRA STRENGTH. No score cutoff separates these
 *   (the second scores a perfect 100), so the UI, not a threshold, is what
 *   stands between the user and a wrong DIN. */
export type NameMatch = 'exact' | 'manufacturer' | 'look_alike';

/** One candidate row from the brains sidecar's reference search, DIN
 * already in the app's canonical 8-digit form. */
export interface DinSuggestion {
  din: string;
  product: string;
  strength: string | null;
  score: number;
  /** Optional so a response from before the 2026-07-30 LASA work — or any
   * caller that does not annotate — degrades to `exact`, i.e. the previous
   * behaviour, rather than warning about everything. */
  name_match?: NameMatch;
  /** The label's own words this candidate's name does not contain. */
  missing_tokens?: string[];
  /** FixbyOPUS3 Task B2: false when this DIN is in the 11,609-DIN profile
   * tier but NOT in the 7,055-DIN appearance tier -- i.e. a real medication
   * that simply cannot be checked from a photo (insulin pens, inhalers,
   * creams, drops, patches). Optional so an older sidecar that does not
   * send the field degrades to "unknown", never to a wrong badge. */
  pill_verifiable?: boolean;
}

/** Response shape for `POST /prescriptions` only -- adds the sidecar's top
 * DIN candidates for the patient's one-tap confirm step. */
export interface PrescriptionWithSuggestions extends Prescription {
  din_suggestions: DinSuggestion[];
}

/* --- Pill scan v2 (Phase 3 -- IMB1 vision + SB2 deterministic matcher via
 * the brains sidecar). This is the ONLY pill-scan response shape; the
 * legacy OpenCV colour/shape/imprint + din_pills candidate-list shape was
 * removed entirely. See `documentation/integration/INTEGRATION_PLAN.md`
 * Phase 3 and `SB2/CONTRACT.md` §4 for the underlying decision contract. */

export type PillDecision = 'verify' | 'reject' | 'abstain';
export type PillAbstainAction = 'ask_to_flip' | 'shortlist';

/** Per-attribute breakdown for one candidate, verbatim from SB2's scorer --
 * mandatory to surface (not debug data), per SB2 CONTRACT.md §4. */
export interface PillCandidateBreakdown {
  S: number;
  colour_score: number;
  shape_score: number;
  type_score: number;
  imprint_exact: boolean;
  imprint_fuzzy: number;
  ask_to_flip: boolean;
  [key: string]: unknown;
}

/** One ranked candidate: SB2's (din, score, breakdown) enriched by the app
 * backend with a product name/strength (SB2 itself only knows DINs). */
export interface PillRankedCandidate {
  din: string;
  score: number;
  breakdown: PillCandidateBreakdown;
  product: string | null;
  strength: string | null;
  active_ingredient: string | null;
}

export interface PillMatch {
  decision: PillDecision;
  /** Canonical 8-digit zero-padded DIN, or null unless decision === 'verify'. */
  matched_din: string | null;
  abstain_action: PillAbstainAction | null;
  disclaimer: string;
  ranked_candidates: PillRankedCandidate[];
}

/** IMB1's raw vision readout -- `colour_modes`/`shape_out`/etc are the SB2
 * input contract fields; the rest are diagnostics-only (still useful for
 * the UI, e.g. `shadow_fusion_suspected`). */
export interface PillRecord {
  detected: boolean;
  photo: string;
  colour_modes?: { top2: [string, number][] }[];
  shape_out?: string;
  shape_conf?: number;
  type_out?: string;
  type_conf?: number;
  imprint_reads?: { i1: string; i3: string };
  bbox?: number[];
  det_conf?: number;
  shadow_fusion_suspected?: boolean;
  colour_calib_method?: string;
  error?: string | null;
}

/** `POST /analyze/pill/v2` response. `status: "no_profile"` is the
 * empty-profile short-circuit (Phase 3) -- the sidecar is never called in
 * that case, so `record`/`match` are both null. */
export interface PillAnalysisV2Response {
  status: 'ok' | 'no_profile';
  message?: string;
  record: PillRecord | null;
  match: PillMatch | null;
}

export interface ScanRecord {
  id: string;
  created_at: string;
  drug_name: string | null;
  match_status: 'matched' | 'unmatched' | 'warning';
  action_taken: string;
  image_filename: string | null;
  detected: boolean | null;
  decision: PillDecision | null;
  abstain_action: PillAbstainAction | null;
  matched_din: string | null;
  top_candidate_score: number | null;
  shadow_fusion_suspected: boolean | null;
}

/* --- BB3 Q&A + CB4 voice (Phase 4). `POST /api/v1/qa/chat` returns one of
 * BB3's 8 frozen statuses (BB3/CONTRACT.md §2) plus this app's
 * `guard_refused` extension -- fields present vary by status, so this is
 * intentionally permissive (optional) rather than a per-status union; the
 * page renders based on `status` and only reads the fields that status
 * actually carries. */

export type QAStatus =
  | 'answered'
  | 'confirm'
  | 'pick_list'
  | 'not_found'
  | 'no_entity'
  | 'enumeration'
  | 'refused_dosing'
  | 'guard_refused';

export type QAVoice = 'cb4' | 'local_7b' | 'none';

/** `resolution.entities`/`candidates`/`family_assumption` are mandatory to
 * surface in the UI (BB3 CONTRACT.md §2) -- they explain *why* BB3 answered
 * about what it answered about, same discipline as SB2's ranked_candidates. */
export interface QAResolution {
  entities: string[];
  din_count: number;
  family_assumption?: string;
  candidates?: { name: string; score: number }[];
}

export interface QASource {
  tag: string;
  section: string | null;
  source: string | null;
  match_status: string | null;
  score: number | null;
  rerank_score: number | null;
}

export interface QAGuardFlags {
  json_degenerate_retried: boolean;
  entity_guard_retried: boolean;
  ingredient_consistency_retried: boolean;
  guard_refused: boolean;
  structural_inconsistency: boolean;
}

export interface QAChatResponse {
  status: QAStatus;
  resolution?: QAResolution;
  abstained?: boolean;
  answer: string;
  sources?: QASource[];
  tier?: string;
  disclaimer?: string;
  cited_tags?: string[];
  priority?: number;
  guard_flags?: QAGuardFlags;
  refused_dosing?: boolean;
  voice: QAVoice;
  model?: string;
}

export interface Patient {
  id: string;
  first_name: string;
  last_name: string;
  date_of_birth: string;
  preferred_language: string;
  phone_number: string | null;
  medications_analyzed: number;
  last_scan_at: string | null;
  notifications_enabled: boolean;
  created_at: string;
}
