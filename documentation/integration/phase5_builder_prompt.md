# Phase 5 Builder Prompt — PRESERVED FOR NEXT SESSION (SA, 2026-07-18)

**Status:** Phase 5 prep is DONE (content pack + assistant KB + logo SVGs shipped, citations
verified); the build was spawned then STOPPED almost immediately (token budget — no files were
written by the builder). Execution happens next session.

**AMENDED 2026-07-19 (SA):** Muthu supplied his own logo (`dev/frontend/public/MyPillSafe_Logo.png`)
and chose an app-surface rebrand to **MyPillSafe** (dev packages, ADR, and the paper keep "PillSafe").
The SA cleaned the asset (a baked fake-transparency checkerboard was removed; `logo.png` +
`logo-mark.png` derived), renamed the content pack + assistant KB, and deleted the three prep SVGs.
Briefing #10, §B, §C/§D/§E brand touches, and the verification bar were amended to match. Spawn the
prompt below as amended.

## Next-session resume steps (SA, in order)

1. ~~Harvest Journey.md~~ **DONE 2026-07-18 (same session):** three additions landed in the
   content pack — landing §1 "Why verify instead of identify?" callout (the 13-identical-DINs
   collision fact); about §2 "How we worked" (4 methodology bullets: measure-the-assumption /
   pre-registered bars / data-decides / every-smoke-test-caught-a-bug + guards' zero failures);
   science §5-C wrong-drug scoping rationale (name-mention asymmetry, stated qualitatively).
   All are corpus/process facts, no dev-set performance metrics. Skip straight to step 2.
2. Spawn a **Sonnet** agent (`general-purpose`, `model: sonnet`) with the ENTIRE prompt below
   (everything after the `---` line), unchanged.
3. When it reports: run the SA verification pass (suites, build, browser click-through at
   360/1280px incl. decision-state panels + live assistant chat + voice endpoint), fill the
   Phase 5 Result in `INTEGRATION_PLAN.md`, flip the status board, append the ADR entry.
4. Reminder also owed in a future session (NOT Phase 5): revise the stale
   `Brainstorm\IMB1_Paper_Draft_Prompt.md` (v1-era numbers, pre-NB07 structure — Muthu
   flagged 2026-07-18).

---

You are building **Phase 5 (UI overhaul)** of the PillSafe app × brains integration, in the app repo `D:\Projects\PillSafe\PillSafe`. Work on Windows (PowerShell). Backend venv: `D:\Projects\PillSafe\PillSafe\dev\backend\venv` (Python 3.12). Frontend: `D:\Projects\PillSafe\PillSafe\dev\frontend` (React SPA + Vite + TypeScript + Tailwind + react-router; node_modules installed).

# Builder Briefing (BINDING — verbatim from the integration plan)

1. **The three brain packages are FROZEN.** Never create, edit, or delete anything under `D:\Projects\PillSafe\IMB1_v0\`, `D:\Projects\PillSafe\SB2\`, `D:\Projects\PillSafe\BB3\`, or `D:\Projects\PillSafe\PillSafeChatbot\`. All changes live in the app repo `D:\Projects\PillSafe\PillSafe\`. Each package's `CONTRACT.md` is authoritative — read it before wiring to it.
2. **Never touch SB2's `WEIGHTS`/`THRESH` or reinterpret its decisions.** `verify`, `reject`, `abstain` are three DISTINCT outcomes; abstain is the COMMON case by design (safety-biased operating point, FA 1.15% held-out). Never collapse abstain into reject. `ranked_candidates` (per-attribute breakdown) and BB3's `resolution` block are mandatory to surface, not debug data.
3. **No cloud API keys in the brains sidecar** — SB2 and BB3 are local-only by design. The only cloud call in the whole system is CB4 (Claude) inside the app backend, using `LLM_API_KEY`.
4. **Two-process constraint:** torch and paddle can never share one process (cuDNN WinError 127). `imb1.analyze_pill()` already spawns its OCR subprocess internally — do not import paddle in the sidecar process, and do not "optimize" the subprocess away.
5. **Disclaimers are mandatory** on every decision-bearing surface: pill-scan results, Q&A answers, DIN confirmations. "Decision-support only — not medical advice. Verify with a pharmacist." The packages return a `disclaimer` field — display it, don't strip it.
6. **Machine/ops:** Windows 11, RTX 4060 8GB. No Ollama running during GPU-heavy work (the 7B holds ~5GB). ultralytics `predict(list)` is one giant batch — chunk it. First model load per process is slow; per-call latency for `analyze_pill` is seconds (Paddle subprocess spawn) — design UX and HTTP timeouts accordingly (≥120s).
7. **Do not commit or push.** Leave changes in the working tree; Muthu commits.
8. **Verification is not optional.** Run the phase's verification bar exactly; report actual outputs (counts, not adjectives). Every prior build's mandated smoke test caught ≥1 real bug.
9. Match the existing codebase's idioms (FastAPI route/service/model layering; React page/component/api-wrapper layering; Tailwind utility classes; existing error envelope `{"detail": {"error": {"code": ..., "message": ...}}}`).
10. **Brand rename (user-facing only): the product name is "MyPillSafe".** The content pack and the assistant KB are ALREADY renamed — transcribe them verbatim as instructed. Additionally sweep all pre-existing user-visible "PillSafe" strings in the app (page titles, headers, footers, auth pages, PWA manifest, aria-labels, toasts) to "MyPillSafe". Do NOT rename: code identifiers, file/directory names, API route paths, env var names, backend config keys, test ids, or any text returned by the frozen packages (e.g. the sidecar's `disclaimer` field passes through unmodified).

# Read FIRST, before writing any code

1. `D:\Projects\PillSafe\PillSafe\documentation\integration\phase5_content_pack.md` — **ALL page copy and widget strings. Transcribe VERBATIM. You may not add statistics, citations, or capability claims not in this pack.**
2. `D:\Projects\PillSafe\PillSafe\dev\backend\app\data\assistant_kb.json` — the assistant knowledge base (already authored; do not edit its content).
3. The design reference (READ-ONLY, do not modify anything under `D:\Projects\PathoIntern_MVP\`):
   - `D:\Projects\PathoIntern_MVP\frontend\tailwind.config.js` (palette)
   - `D:\Projects\PathoIntern_MVP\frontend\src\app\page.tsx` (landing layout patterns)
   - `D:\Projects\PathoIntern_MVP\frontend\src\app\about\vision\page.tsx`, `...\problem\page.tsx`, `...\team\page.tsx` (about-page patterns)
   - `D:\Projects\PathoIntern_MVP\frontend\src\components\AboutNav.tsx` (prev/next chain)
   - `D:\Projects\PathoIntern_MVP\frontend\src\components\VoiceChatbot.tsx` (chat widget UX — your widget mirrors this)
   - `D:\Projects\PathoIntern_MVP\backend\app\api\chatbot.py` (confidence-zone endpoint design)
4. Current app: `dev/frontend/src/` (router, layouts, pages, tailwind.config.ts, ui components), `dev/backend/app/` (routes, services, config, tests). Logo assets already exist in `dev/frontend/public/`: `logo.png`, `logo-mark.png` (see §B).

# Build spec

## A. Design tokens (PathoIntern palette adoption)
In `dev/frontend/tailwind.config.ts` + `src/styles/globals.css`:
- New brand tokens: `navy: #1E3A5F` (new primary), `teal: #2A9D8F` (accent — REPLACES the old teal scale as the accent value; you may keep a small scale derived from #2A9D8F), `coral: #D64045`, `burnt: #E76F51`, `light: #E8EEF2`. Font stays Inter.
- Remap the existing `primary` token family to navy (`DEFAULT #1E3A5F`, `dark #162B47`, `light #E8EEF2`) so existing `bg-primary`/`text-primary` usages restyle globally; sweep pages for hardcoded old-green/old-teal classes and migrate them.
- `brand-hero` gradient → navy version (`linear-gradient(135deg,#162B47 0%,#1E3A5F 55%,#2A9D8F 140%)` or similar).
- **FROZEN, byte-identical: the `success`, `warning`, `danger` token values.** verify=green / abstain=amber / reject=red decision semantics are binding (Phase 3). Do not restyle `PillResultPanel` decision colours, and never use coral on any decision-bearing surface (it reads as red).
- Add PathoIntern niceties: card-hover lift, page fade-in, teal `:focus-visible` ring. Base font ≥16px, touch targets ≥44px, WCAG 2.2 AA contrast.

## B. Logo wiring + icons (AMENDED 2026-07-19 — Muthu's logo, MyPillSafe brand)
- Brand assets already in `dev/frontend/public/` (SA-prepared; use as-is, never re-derive or edit):
  - `logo.png` (653×521, transparent, trimmed lockup: mark + "MyPillSafe" wordmark) — the default logo in UI.
  - `logo-mark.png` (400×400, transparent, mark only) — Sidebar collapsed state; source for favicon + PWA icons.
  - `MyPillSafe_Logo.png` — the original source asset; keep untouched, do NOT reference it in code.
  - The three earlier SVGs (`logo.svg`, `logo-white.svg`, `logo-mark.svg`) are DELETED — ensure no references.
- **BINDING dark-surface rule:** the wordmark and mark linework are navy — `logo.png`/`logo-mark.png` must NEVER sit directly on navy/dark surfaces. On any dark surface (navy Topbar, hero, dark footer) the logo sits inside a white rounded chip/panel (PathoIntern hero pattern; e.g. `bg-white rounded-lg px-3 py-1`, logo ~`h-8` in the Topbar chip). On white/light surfaces use it directly.
- `index.html`: title "MyPillSafe — Canadian medication safety, verified", favicon links → the generated PNGs below, `theme-color` #1E3A5F, Inter font link if not present.
- Icon generation: add `dev/frontend/scripts/generate-icons.mjs` using `sharp` (devDependency) rendering from `logo-mark.png`: `favicon-32.png`, `apple-touch-icon.png` (180), `pwa-192.png`, `pwa-512.png`, `pwa-maskable-512.png` (mark scaled to ~78% centered on WHITE #FFFFFF — not navy: the mark's linework is navy). Run it; leave outputs in `public/` (uncommitted, like everything else).

## C. Public content chain (PathoIntern-style)
Routes (update `src/router/index.tsx`; all under `PublicLayout`):
- `/` LandingPage — REBUILD per content pack §1: navy hero (badge, headline, sub, CTAs, white logo panel right), "How MyPillSafe Works" 4 step cards (border-t-4 accent pattern), "Three-Outcome Safety Design" 4-card grid **using the real semantic decision colours** (green/amber/red/navy per pack), Scientific Foundation strip (navy section, 4 border-l-4 cards, links to /about/science), closing CTA, footer disclaimer.
- `/about` AboutPage — rewrite per pack §2 (What MyPillSafe Is, Five Brains as 5 cards, Why this architecture, scope note).
- `/about/vision` VisionPage — pack §3 (mission hero, vision, 4 value cards).
- `/about/problem` ProblemPage — pack §4 (2 CIHI stat cards, body sections, closing line).
- `/about/science` SciencePage — pack §5 (Section A: 8 citation cards; Section B: "In Preparation" badge block with the working title + honest status VERBATIM incl. the pending-confirmatory-study sentence; Section C: 3 principle cards).
- `/about/team` TeamPage — pack §6 (5 members, initial-letter avatars, no photos; Conestoga note).
- New `src/components/AboutNav.tsx` mirroring PathoIntern's prev/next chain, order per pack §7 (last Next = "Get Started" → /register, coral button). Public navbar in `PublicLayout` gains an About dropdown/links + hamburger on mobile. ContactPage: restyle only, linked from footer.
- New public pages ship in English exactly as in the pack (no i18n keys needed for them).

## D. MyPillSafe Assistant (floating explainer chatbot — PathoIntern parity)
**Backend** (`dev/backend`):
- `app/services/assistant_kb.py`: load `app/data/assistant_kb.json`; retrieval = rapidfuzz `token_set_ratio` of the query against each entry's `question` + `question_fr` (best of the two), score 0–100. Confidence zones (mirroring PathoIntern's design, calibrated for fuzzy scores): ≥60 → LLM answer path (top-3 entries as context, suggested_questions = next-best KB questions); 40–59 → clarification (top-3 KB questions as options, no LLM call); <40 → out-of-scope fallback string (from content pack §8) + suggestions.
- Medication-intent gate BEFORE retrieval: a keyword/regex heuristic (dose, dosage, mg, take/prendre, interaction, side effect/effet secondaire, pregnant, alcohol, plus a "looks like a drug name question" pattern like "can I take X"). On trigger → return the med-redirect string (pack §8) with `redirect_to_qa: true`, no LLM call. The CB4 system prompt ALSO enforces the redirect (belt and suspenders).
- `app/services/assistant_service.py`: CB4 generation reusing the existing anthropic client pattern from `cb4_service.py` (same `LLM_API_KEY`/`LLM_MODEL` config; max_tokens ≤500). System prompt implements content pack §8's binding requirements (answer ONLY from provided KB context, explainer scope only, never medication answers → redirect, answer in requested language en/fr, ≤180 words, no stats beyond the context, capstone honesty). History: last 10 turns mapped bot→assistant.
- `app/routes/assistant.py`: **public** (no auth) `POST /api/v1/assistant/chat` `{query, language?, history?}` → `{response, language, confidence, sources[{question,category,score}], latency, used_llm, suggested_questions, clarification_needed, clarification_options, redirect_to_qa}`. `POST /api/v1/assistant/voice` (multipart `audio`, form `language`) → `{text}` via **faster-whisper** "base", CPU, int8, lazy singleton (add `faster-whisper` to requirements + install in venv). LLM failure → serve top KB answer directly with `used_llm: false` (PathoIntern's fallback pattern).
- Rate limiting (public endpoints): 10/min/IP chat, 5/min/IP voice. Use `slowapi` if it drops in cleanly; otherwise a small in-process sliding-window dependency (~20 lines) — must be unit-testable. 429 uses the standard error envelope.
- Tests (mock the anthropic client and the transcriber): zone routing (high/clarify/fallback), med-intent redirect, KB retrieval sanity, rate-limit 429, voice endpoint happy path + bad file. All existing tests must stay green.

**Frontend**:
- `src/components/AssistantWidget.tsx` closely mirroring PathoIntern's `VoiceChatbot.tsx` UX: FAB bottom-right → 320–384px × ~580px window; navy header with badge + EN/FR pill toggle + close; amber disclaimer strip; message bubbles (user navy right / bot white left); confidence badge, sources toggle panel, clarification option buttons, suggested-question chips; thinking dots; input row with send + hold-to-record mic (MediaRecorder → `/assistant/voice` → transcript → send, `speechSynthesis` speaks the reply only for voice-initiated turns, cancel on unmount); strings VERBATIM from pack §8; `redirect_to_qa` responses render a button → `/dashboard/qa` if authenticated else `/login`.
- Mount in `PublicLayout` and `AppShell` — but HIDE on `/dashboard/qa` (never two chat UIs on one screen).

## E. PWA + mobile pass
- `vite-plugin-pwa` (autoUpdate): manifest name "MyPillSafe", short_name "MyPillSafe", description from pack hero sub-headline, `theme_color #1E3A5F`, `background_color #FFFFFF`, display standalone, icons 192/512 + maskable. **Precache the static shell only; `/api/**` must be NetworkOnly — no offline-API pretense.**
- Mobile-first pass on key flows (auth, dashboard, analyze/camera, medications, Q&A, records, public pages): dashboard gets a bottom-tab bar under `md:` (Home, Analyze, Meds, Q&A, Records; sidebar hidden), public navbar hamburger, single-column cards, camera capture full-bleed, no horizontal scroll at 360px.
- Restyle remaining dashboard/auth/admin pages to the new tokens (Cards/Buttons/Alerts refresh). Do NOT change page logic. QAChatPage/DinLinkPanel: token restyle only. **PillResultPanel: do not touch its decision colour semantics.**
- Small deferred fix from Phase 3 (in scope now): Safety Records "Drug Detected" column must show the matched product/DIN on verify rows instead of "Unknown" (data already persisted on the scan row).

# Out of scope
BB3/sidecar changes (not needed this phase — do NOT start the sidecar or Ollama), Docker, README rewrite (Phase 6), i18n of the new public pages, deleting QAChatPage (it STAYS — architectural decision).

# Verification bar (run ALL, report actual counts/outputs)
1. Backend: full pytest suite green in `dev/backend/venv` (was 93 passing; report new total).
2. Frontend: `npm run type-check` and `npm run build` clean; icon script ran (list generated files); build output contains the PWA manifest + service worker.
3. Live smoke (backend on :8000 via venv uvicorn, frontend dev server): (a) one REAL `/assistant/chat` call with the live CB4 key from `dev/backend/.env` — ask "What is MyPillSafe?" — assert `used_llm: true` and an on-scope answer; (b) one med-intent query ("can I take ibuprofen with warfarin?") — assert `redirect_to_qa: true` and NO LLM call; (c) one clarification-zone and one fallback-zone query; (d) `/assistant/voice`: generate a short WAV via PowerShell `System.Speech` saying "What is My Pill Safe" and POST it — assert the transcript fuzzy-contains "pill safe"/"pillsafe" (case/space-insensitive). Kill servers after.
4. Confirm frozen decision tokens: `success/warning/danger` values in tailwind config unchanged (diff vs git HEAD) and PillResultPanel imports/classes untouched except inherited font/spacing.
5. Brand sweep check: `grep -rn "PillSafe" dev/frontend/src dev/frontend/index.html` — report every remaining occurrence that is NOT part of "MyPillSafe" and justify each (must be code identifiers or frozen-package pass-through only, never user-visible copy).
6. `git status` summary of changed/added files. Commit NOTHING.

# Report back
Files created/modified (grouped), all verification outputs with real counts, any deviations from this spec with reasons, any bugs found in existing code (report, don't silently fix unless trivial and in-scope), and anything the SA must re-verify by hand.
