# OptimizationChangePlan

**Date:** 2026-08-15  
**Repository:** D:\Projects\PillSafe\PillSafe  
**Produced by:** Orchestrated inventory→analysis agent chain (Haiku inventory, Sonnet/Opus analysis)  
**Status:** DRAFT — no change has been executed.

## Scope

This plan covers GOAL 1 (remove PaddleOCR from the IMB1 pipeline) and GOAL 3 (restructure into Development / Quality / Production tiers). GOAL 2 (deploy IMB1 on a DigitalOcean droplet) was evaluated and EXCLUDED by owner decision on 2026-08-15 — infeasible on the current 2 vCPU / 4 GB non-GPU droplet; the analysis remains in the session record only.

## Executive summary

- **GOAL 1:** Remove the legacy PaddleOCR dual-read imprint path from IMB1, freeing ~490 MB of disk cache and collapsing the record shape to one variant. This must wait for the two-stage reader to prove itself (14+ consecutive days, ≥200 live scans, zero reader-caused 422s) before deletion, since the legacy path is currently the only rollback mechanism.

- **GOAL 3:** Restructure the repo into Development/, Quality/, and Production/ tiers via shallow renames: approximately 297 tracked files move via `git mv` (zero content risk, history preserved), with roughly 8 files requiring path-string edits instead. This approach avoids the cost of decoupling colocated tests from their source.

---

## GOAL 1 — Remove PaddleOCR from the IMB1 Pipeline

### Summary (2–3 sentences)

IMB1 has exactly one PaddleOCR-dependent code path — the legacy dual-read imprint reader (`imb1/ocr_sub.py`, spawned from `imb1/__init__.py:111`) — which runs only when `PILLSAFE_READER=off` (the factory default) or when the new VLM two-stage reader's session fails to build (`production_wiring.py:382–448`, silent fallback). Removing this path deletes real code, frees ~490 MB of on-disk model caches on IMB1-only hosts, and collapses IMB1's record shape from two variants (legacy `imprint_reads` vs. C6 `faces[]`) to one — but it also deletes the only rollback mechanism M1 currently has, so it must not happen before the two-stage reader has demonstrated it doesn't need that rollback. OB5's PaddleOCR usage (`rx_ocr_sub.py`) is architecturally untouched and stays pinned in `dev/brains/requirements.txt`.

### Scope: in / out

**In scope (IMB1 legacy imprint path only):**
- `IMB1_v0/imb1/ocr_sub.py` — the paddle dual-read subprocess module
- `IMB1_v0/imb1/__init__.py` — the spawn wrapper and its call site
- `IMB1_v0/requirements.txt` — the paddle pins (IMB1_v0 copy only)
- `dev/brains/production_wiring.py` — the session-failure fallback branch and stale legacy-shape docstring
- `dev/brains/config.py` — `PILLSAFE_READER` semantics/default
- `dev/brains/smoke_test.py` — the legacy-shape test assertion
- On-disk caches `~/.paddleocr/` and `~/.paddlex/` (IMB1-only hosts)

**Out of scope (explicit):**
- `dev/brains/rx_ocr_sub.py`, `dev/brains/app.py`, and `dev/brains/requirements.txt`'s paddle pins — OB5 (prescription OCR) keeps PaddleOCR permanently; it is the sole prescription-OCR mechanism and has no replacement in flight.
- The modelscope torch-stub / subprocess-isolation technique (Windows torch↔paddle mutual exclusion) — still required for OB5 regardless of what happens in IMB1.
- `IMB1_v0/src/nb08_read16.py` and `nb08_read16_vlm.py` — historical baseline-comparison scripts; documentation of a past measurement, not live code paths.
- `nb08_imb1.py`'s `build_record()` reader=None branch — this returns an empty `faces: []`, it does not spawn `ocr_sub.py`, so it is not a paddle path and needs no change.

### Files to Modify / Delete

| path | action | what |
|---|---|---|
| `IMB1_v0/imb1/ocr_sub.py:1–70` | Delete | Entire paddle dual-read module (I1 raw + I3 CLAHE); imports `PaddleOCR` at line 59 |
| `IMB1_v0/imb1/__init__.py:29–89, 111` | Modify | Remove `_OCR_SUB` path constant, `_run_ocr_subprocess()`, the UTF-8 subprocess-encoding contract (lines 44–90), and the call site inside `analyze_pill()` at line 111 |
| `IMB1_v0/imb1/pipeline.py:7–8` | Modify | Update/remove docstring claiming imprint OCR is a "SEPARATE paddle-only subprocess" |
| `IMB1_v0/requirements.txt:15–16` | Modify | Drop `paddleocr==3.7.0`, `paddlepaddle-gpu==3.3.1` (IMB1_v0 copy only) |
| `dev/brains/config.py:49–62` | Modify | Redefine `PILLSAFE_READER` so `"off"` can no longer resolve to the (now-deleted) legacy paddle path |
| `dev/brains/production_wiring.py:382–448` | Modify | Remove the `session=None → legacy ocr_sub` fallback branch in `analyze()`; a failed session build must raise `ReaderError`/422, consistent with the no-fallback stance already declared at lines 147–155 |
| `dev/brains/production_wiring.py:59–68` | Modify | Docstring describing the legacy `imprint_reads` record shape becomes dead documentation; remove or mark historical |
| `dev/brains/smoke_test.py:145–147` | Modify | Replace `assert "imprint_reads" in record` (legacy shape) with a C6-contract assertion (`contract_version`, `faces[]`) |
| `C:\Users\muthu\.paddleocr\` (cache) | Delete | 221.87 MB, IMB1-only hosts |
| `C:\Users\muthu\.paddlex\` (cache) | Delete | 268.48 MB, IMB1-only hosts |

### Contracts touched

- **IMB1→SB2 record shape:** collapses from two variants to one. Legacy shape (`colour_modes, shape_out, type_out, imprint_reads: {i1, i3}`, no `contract_version`) disappears; only the C6 shape (`contract_version`, `faces[]`, `lexicon_id`, ...) remains reachable. Any downstream code (SB2, frontend) still branching on the legacy shape becomes dead code and should be identified separately.
- **`PILLSAFE_READER` semantics:** `"off"` currently means "run the legacy paddle path" (`config.py:49–62`) and is the documented factory default and M1 rollback switch. Post-removal, `"off"` must either be rejected at startup/config-validation (fail fast, clear error) or redefined to mean something else entirely — it cannot silently no-op into a 422 discovered only at first request.
- **Test assertions:** `smoke_test.py:145–147` currently asserts the legacy shape as a first-class supported outcome. This assertion must be replaced, not just deleted, or IMB1 test coverage silently shrinks.

### Risks (ordered, rollback loss first)

1. **Rollback loss.** `ocr_sub.py` is the only documented M1 rollback mechanism. Once deleted, a misbehaving two-stage reader in production has no legacy path to degrade to — only 422s. This is the governing risk and is why sequencing (below) gates removal behind a soak period.
2. **Two independent trigger points, one deletion.** Both `config.py`'s default `"off"` AND `production_wiring.py`'s `session=None` fallback currently route to the same `ocr_sub.py` code. Fixing only one and deleting the file anyway turns the other into an unhandled `ImportError` deep in a subprocess (ugly 500) instead of a clean 422 — both call sites must be closed before deletion.
3. **Stale architecture documentation.** `pipeline.py` and `production_wiring.py` docstrings describe a "separate paddle-only subprocess" for IMB1; left unedited, they mislead future readers into thinking paddle is still in the IMB1 path.
4. **Per-host cache accounting.** Freed disk is per-workstation/server, not global. Any host that also runs OB5 (e.g., shared `dev/brains` dev boxes) must keep the caches; only IMB1-only hosts get the full ~490 MB back. Re-adding paddle later on a cleaned host means a re-download.
5. **Test coverage regression.** If `smoke_test.py`'s legacy assertion is deleted rather than replaced, IMB1's test suite loses a shape-contract check without an equivalent replacement.

### Sequencing & verification

0. **Gating precondition — soak criterion.** Do not start step 1 until the two-stage reader has run as the effective production default for **N consecutive days (proposed: 14) covering at least M live scans (proposed: ≥200)** with **zero reader-caused 422s (`READER_ERROR_RETRYABLE`)**. Any reader-caused 422 in the window resets the clock. Pass bar: soak log/dashboard query shows 0 qualifying 422s over the full window.
1. Flip `PILLSAFE_READER` factory default from `"off"` to `"two_stage"` in `config.py`, keeping `ocr_sub.py` in place as a manual-only escape hatch (no deletion yet). Pass bar: an install with no env var set exercises the two_stage path; existing C6 smoke assertions pass.
2. Remove the `session=None → legacy` fallback branch in `production_wiring.py:382–448`. Pass bar: a forced session-build failure (test double / unreachable VLM endpoint) returns 422 `READER_ERROR_RETRYABLE`, never a legacy-shape 200.
3. Re-run the step-0 soak criterion for a second window under this stricter no-fallback behavior — this is the real "no rollback" production shape. Pass bar: same zero-422 threshold, met under live deployment, not just test doubles.
4. Delete `imb1/ocr_sub.py`, `_OCR_SUB`/`_run_ocr_subprocess`, the call site at `__init__.py:111`, and the `IMB1_v0/requirements.txt` paddle pins. Pass bar: `grep -r paddleocr IMB1_v0/` returns zero hits outside historical comparison scripts; full IMB1 test suite is green on `PILLSAFE_READER=two_stage`; setting `PILLSAFE_READER=off` now fails fast at config load with a clear error, not a runtime `ImportError` mid-request.
5. Replace the legacy assertion in `smoke_test.py`. Pass bar: no reference to `imprint_reads` remains; a `contract_version`/`faces[]` assertion passes.
6. Delete `~/.paddleocr/` and `~/.paddlex/` on IMB1-only hosts; leave untouched on any host still running OB5. Pass bar: folder-size check confirms ~490 MB freed on IMB1-only hosts; OB5 sidecar hosts confirm paddle still importable via existing `rx_ocr_sub.py` health check.
7. Clean up stale docstrings (`pipeline.py:7–8`, `production_wiring.py:59–68`). Pass bar: no remaining IMB1-facing text implies paddle runs in the IMB1 path; doc review sign-off.

### Expected payoff

- **Disk:** ~490 MB freed (`~/.paddleocr/` 221.87 MB + `~/.paddlex/` 268.48 MB) — but only on hosts that don't also run OB5. Shared hosts (any box running `dev/brains` for OB5) keep both caches; this is a host-topology-dependent win, not a blanket one.
- **Code paths deleted:** `imb1/ocr_sub.py` (~70 lines), `_run_ocr_subprocess`/`_OCR_SUB` and the UTF-8 encoding-contract plumbing in `imb1/__init__.py` (~60 lines), one call site, the `production_wiring.py` fallback branch, and one legacy test assertion — roughly 150–200 lines of production/test code, plus one fewer record shape for every downstream consumer to branch on.
- **Dependency table: unchanged where it matters.** `dev/brains/requirements.txt` keeps `paddleocr==3.7.0` and `paddlepaddle-gpu==3.3.1` unconditionally, because OB5 needs them. This is an `IMB1_v0/requirements.txt`-only pin removal, not an org-wide dependency drop. The Windows torch/paddle subprocess-isolation architecture, the modelscope torch-stub trick, and the version-tolerant PaddleOCR constructor all remain fully in place for OB5's `rx_ocr_sub.py` — none of that engineering goes away.

### Owner summary

Here's the honest version of what "removing PaddleOCR from IMB1" actually gets us, and what it doesn't.

**What it buys:** IMB1 (the pill-vision/imprint reader) currently has two separate ways of reading a pill's imprint — the old PaddleOCR-based dual-read subprocess, and the new VLM-based two-stage reader that shipped as M1 on 2026-08-14. Once we're confident the new reader doesn't need a safety net, we can delete the old one entirely: about 150–200 lines of code, one whole subprocess file, a config branch, and a stale test assertion. We also get back roughly 490 MB of disk space from PaddleOCR's model-weight caches — but only on machines that exclusively run IMB1. Any machine that also serves prescription-label OCR keeps those caches, for reasons below. On top of the cleanup, IMB1 stops emitting two different shapes of result record and settles on one, which simplifies everything downstream that consumes it.

**What it cannot buy:** PaddleOCR is not going away from PillSafe. It's the only mechanism we have for reading prescription labels (a completely separate feature, called OB5), and that code path is untouched by this work — same dependency, same install size, same Windows-specific engineering to keep it from conflicting with our other OCR engine. So this is IMB1-only cleanup, not a project-wide "drop a dependency" win.

**The risk that matters most:** the old PaddleOCR path is currently our only rollback mechanism for the new reader. It's both the factory default (nothing has explicitly turned it off yet) and the automatic fallback if the new reader's setup ever fails. Delete it today and we've deleted our safety net before we know we don't need one. So I'm proposing we don't touch any code until the new reader has proven itself in production: my suggested bar is 14 consecutive days and at least 200 real scans with zero reader-caused failures. If a failure happens during that window, the clock resets. Only after that — and after we've deliberately turned off the automatic fallback and re-run the same soak test under those stricter conditions — do we actually delete the old code.

**Effort:** seven sequenced steps, each with a concrete pass/fail check, spanning roughly a dozen files plus two disk-cache locations. Most steps are small, mechanical edits; the two soak-test waiting periods (step 0 and step 3) are the actual time cost, not the coding.

---

## GOAL 3 — Restructure into Development / Quality / Production

### Summary (2–3 sentences)

The repo's real content already sorts cleanly into three tiers, so the honest move is a shallow re-map, not a rebuild: `dev/` becomes `Development/` and `docker/` becomes `Production/docker/` as straight `git mv` renames (≈297 tracked files, zero content risk, history preserved), `documentation/deployment/` splits between a new `Production/deploy/` and a new `Quality/`, and colocated unit tests, `.github/`, `Makefile`, and root platform configs stay exactly where they are. That leaves roughly **8 files needing real content edits** (path strings) against **~297 files that are pure renames** — versus a "deep" version that also drags colocated tests out of `src/` and `tests/`, which would touch 50+ additional files (build configs, imports, CI glob patterns) for no functional gain, since relocated tests still need the same source-adjacent fixtures. Recommendation: do the shallow version.

### Proposed semantics of the three folders

- **Development/** — the three app source trees as they exist today: `dev/backend/`, `dev/brains/`, `dev/frontend/`, each carrying their own colocated tests, configs, and Dockerfiles. This is "what a developer edits to change behavior." Runtime data folders (`uploads/`, `brains/data/`) stay nested inside their owning service — they are not source, but they're too tightly coupled to relocate without runtime path changes, which is out of scope here.
- **Quality/** — NOT unit tests (those stay colocated by design — see Constraints). Quality is cross-cutting QA *evidence and tooling* that currently has no real home: `documentation/evaluation/` (rx_parsing, din_lasa), E2E findings and red-team briefs presently misfiled under `documentation/deployment/`, standalone probe/harness scripts, and the two categories the task explicitly calls out as extractable from `dev/backend/tests/` without breaking pytest discovery — generated test-run **artifacts** (`tests/artifacts/`, binary output, not source) and the standalone **mutation-testing** scripts (`mutation_t04.py`, `mutation_t09a.py`), which are QA technique, not app-adjacent unit coverage.
- **Production/** — everything that exists to build, ship, and run the deployed system: `docker/` (compose files, nginx configs) and the deploy-guide half of `documentation/deployment/` (DEPLOY_GUIDE*.md, sidecar/runbook docs, restart checklists). `Makefile` and `.github/workflows/ci.yml` conceptually belong to this tier too but are pinned at root by hard constraints (below), so they stay put with their internal paths updated instead of moving.

### Target structure (tree) and old→new mapping table

```
PillSafe/
├── .github/                         [UNCHANGED — GitHub Actions requirement]
├── .claude/                         [UNCHANGED — tool config]
├── Development/
│   ├── backend/                     (was dev/backend/)
│   │   ├── app/, migrations/, scripts/, uploads/
│   │   ├── tests/                   (colocated pytest STAYS, minus artifacts/ + mutation_t*.py)
│   │   └── Dockerfile, pytest.ini, requirements*.txt
│   ├── brains/                      (was dev/brains/, incl. data/, tests/)
│   └── frontend/                    (was dev/frontend/)
│       ├── src/                     (colocated *.test.ts* STAYS)
│       ├── public/, vitest.config.ts
│       └── Dockerfile, package.json
├── Quality/                          [NEW]
│   ├── evaluation/                  (was documentation/evaluation/)
│   ├── findings/                    (was E2ETestingFindings.md, LLM_Rx_Parsing_RedTeam_Brief.md)
│   ├── harnesses/                   (was redteam_llm_extraction.py, probe_lasa.py)
│   └── backend/
│       ├── artifacts/               (was dev/backend/tests/artifacts/)
│       └── mutation/                (was dev/backend/tests/mutation_t04.py, mutation_t09a.py)
├── Production/                       [NEW]
│   ├── docker/                      (was docker/, incl. nginx/)
│   └── deploy/                      (was documentation/deployment/, minus QA docs above)
├── documentation/                    [REMAINS — general/architecture, not QA or deploy]
│   ├── integration/, Poster/, cloudspecs.txt, README.md
├── Makefile                          [UNCHANGED — see Constraints]
├── render.yaml, vercel.json, .env*.example, README.md   [UNCHANGED — root platform convention]
```

| Old path | New path | Move type | Notes |
|---|---|---|---|
| `dev/backend/` | `Development/backend/` | `git mv` (rename) | ~115 tracked files (uploads/ is data, likely gitignored, excluded from count) |
| `dev/brains/` | `Development/brains/` | `git mv` | ~19 tracked files (`.venv` excluded) |
| `dev/frontend/` | `Development/frontend/` | `git mv` | ~123 tracked files (`dist/`, `node_modules/` gitignored, excluded) |
| `docker/` | `Production/docker/` | `git mv` | 7 files; build-context depth changes (see Files to update) |
| `documentation/deployment/DEPLOY_GUIDE*.md`, `Futureworks.md`, `sidecar_apple.md`, `multipilldeploy.md`, `postrestartchecklist.md`, `partA_builder_prompt.md`, `Fixby*.md`, `UI_FirstImpression*.md` | `Production/deploy/` | `git mv` | ~9 files |
| `documentation/deployment/E2ETestingFindings.md`, `LLM_Rx_Parsing_RedTeam_Brief.md` | `Quality/findings/` | `git mv` | 2 files |
| `documentation/deployment/redteam_llm_extraction.py` | `Quality/harnesses/` | `git mv` | 1 file; verify no relative imports |
| `documentation/evaluation/` | `Quality/evaluation/` | `git mv` | ~5–6 files |
| `dev/backend/tests/artifacts/` | `Quality/backend/artifacts/` | `git mv` | 12 files; **verify conftest.py doesn't reference by relative path first** |
| `dev/backend/tests/mutation_t04.py`, `mutation_t09a.py` | `Quality/backend/mutation/` | `git mv` | 2 files; **verify pytest.ini `testpaths`/CI glob still discovers them, or add an explicit CI step** |
| `dev/backend/tests/` (remainder), `dev/frontend/src/**/*.test.ts*`, `vitest.config.ts`, `dev/brains/tests/` | `Development/.../` (implicit, parent rename only) | `git mv` (implicit) | colocated tests STAY — see Constraints |
| `.github/`, `Makefile`, `render.yaml`, `vercel.json`, `.env*.example`, `documentation/integration/`, `documentation/Poster/` | unchanged | content-edit only, or none | see Constraints |

### Files to update (path couplings, file:line rows from the inventory)

| File | Lines | What changes |
|---|---|---|
| `.github/workflows/ci.yml` | 22, 25, 28, 46, 49 | `dev/backend` → `Development/backend`, `dev/frontend` → `Development/frontend` (5 strings) |
| `docker/docker-compose.yml` → `Production/docker/docker-compose.yml` | 58, 120 | `context: ../dev/backend` → `../../Development/backend`; same for frontend (depth increases by one level) |
| `Makefile` | 5, 62, 66, 70, 74 | `-f docker/docker-compose.yml` → `-f Production/docker/docker-compose.yml`; `cd dev/backend`/`dev/frontend`/`dev/brains` → `cd Development/...` |
| `documentation/deployment/DEPLOY_GUIDE_M1_TwoStageReader.md` → `Production/deploy/DEPLOY_GUIDE_M1_TwoStageReader.md` | 36, 41, 46, 53 | `dev/brains/` references and the absolute Windows path example → `Development/brains/` |
| `docker/docker-compose.prod.yml` → `Production/docker/docker-compose.prod.yml` | 4, 7, 96–111 | comment + `.env` lookup path stay relative to its own new location; verify against base compose |
| `dev/backend/Dockerfile`, `dev/frontend/Dockerfile` | comments only | low-severity, cosmetic path-comment updates |
| `dev/backend/app/core/config.py` | comment ~L73 | cosmetic comment update citing `dev/brains/` |

### Constraints that bend the ideal (what cannot move and why)

1. **`.github/` stays at repo root** — GitHub Actions only discovers workflows at `.github/workflows/`; non-negotiable.
2. **Colocated unit tests stay colocated** — `dev/backend/tests/` uses `conftest.py` fixtures and relative imports against `app/`; vitest's default discovery is `src/**/*.test.ts*`. Moving either breaks discovery/imports for no gain; this is standard practice, not a shortcut.
3. **`Makefile` stays at root** — it is the single daily developer entrypoint (flagged CRITICAL in the inventory). Relocating it adds `-f`/`-C` friction while still requiring every internal path to be edited regardless of where `dev/`/`docker/` land — no structural benefit, real daily-workflow cost.
4. **`render.yaml`, `vercel.json` likely stay at root** — Render and Vercel default to reading these from the repo root; treat as the same class of constraint as `.github/` until each platform's dashboard settings are confirmed (not verified in this pass — flag as a pre-move check).
5. **`dev/backend/uploads/` and `dev/brains/data/` stay nested in Development/** — genuinely data, not source, but relocating them means editing runtime file-path code, which is a separate goal from a folder restructure.
6. **`Quality/backend/artifacts/` and `Quality/backend/mutation/` are conditional moves** — the inventory did not trace whether `conftest.py` or other test files reference `tests/artifacts/` by relative path; confirm before moving, not after.

### Risks (dirty tree first, ordered)

1. **Dirty tree / in-flight tray feature (HIGHEST)** — 73 dirty files, 59 of them untracked (T04). `git mv` only operates on tracked files, so untracked tray files under `dev/backend/` and `dev/frontend/` would not follow the rename automatically and could be silently orphaned at old paths.
2. **CI breakage** — unedited `ci.yml` paths turn every workflow run red immediately after the rename lands.
3. **Docker build breakage** — wrong build-context depth halts local dev and prod builds simultaneously.
4. **Deploy-guide drift on a live system** — `DEPLOY_GUIDE_M1_TwoStageReader.md` documents a live laptop-sidecar deploy; stale `dev/brains/` paths cause the next executor to follow instructions that no longer resolve.
5. **Unverified test-artifact/mutation-test relative references** — moving `tests/artifacts/` or `mutation_t*.py` before confirming they're not path-referenced elsewhere risks a quiet pytest failure.
6. **Unverified Render/Vercel root-config assumption** — would only surface at the next platform deploy, after the restructure is already merged.
7. **Documentation cross-reference rot** — docs inside `documentation/` linking to now-moved paths in `Production/deploy/` or `Quality/`; cosmetic, low priority.

### Sequencing & verification (numbered steps, each with a measurable pass bar)

1. Merge `feat/admin-approval-contact-team` (and land the in-flight tray/T04 work) to `main`. **Pass bar:** `git status` on `main` shows 0 modified, 0 untracked.
2. Cut a new `restructure/` branch off clean `main`.
3. Execute the `git mv` operations from the mapping table in one commit or a short stack. **Pass bar:** `git log --follow` on 3 sampled files (`Development/backend/app/main.py`, `Production/docker/docker-compose.yml`, `Quality/evaluation/rx_parsing/README.md`) shows pre-move history intact.
4. Edit the 8 path-coupling files listed above. **Pass bar:** `grep -rn "dev/backend\|dev/frontend\|dev/brains"` across `.github/`, `Makefile`, `Production/docker/` returns zero unintended matches.
5. Local Docker build. **Pass bar:** `docker compose -f Production/docker/docker-compose.yml build` exits 0 for both services.
6. Local Makefile smoke test. **Pass bar:** `make backend`, `make frontend`, `make brains` each start successfully from the new paths.
7. Baseline capture, then re-run: `pytest` from `Development/backend` and `vitest run` from `Development/frontend`. **Pass bar:** identical pass counts to a baseline captured on `main` before step 2.
8. Push branch, open PR. **Pass bar:** GitHub Actions run on the PR is fully green — this is the only authoritative proof `ci.yml` is correct in the cloud, not local success.
9. Deploy-guide dry-read: walk `Production/deploy/DEPLOY_GUIDE_M1_TwoStageReader.md` top to bottom against the new tree without executing destructive steps. **Pass bar:** every path cited resolves to an existing file/dir, 0 dangling references.
10. Merge to `main` only after steps 5–9 all pass.

---

## Evidence & inputs

The following source files were used to build this plan:

- **A1_paddle_inventory.md** — Haiku inventory scan of PaddleOCR usage across the repo (session scratchpad, ephemeral).
- **A3_repo_structure.md** — Haiku directory and file-coupling inventory (session scratchpad, ephemeral).
- **documentation/cloudspecs.txt** — Live DigitalOcean droplet specifications captured 2026-08-15 (2 vCPU, 4 GB RAM, non-GPU); used by the excluded GOAL 2 analysis.
