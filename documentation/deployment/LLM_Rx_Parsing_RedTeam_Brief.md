# Red-Team Brief — "Use an LLM to parse the prescription after PaddleOCR"

**Written:** 2026-07-28, by /pillsafe SA (Opus), at the end of the FixbySonnet1-leftovers session.
**Audience:** the next session's red-team pass (Fable), to decide whether the Rx-parsing path needs a
**redesign** rather than more regex patches.
**Sequencing (Muthu's call):** this red-team runs **BEFORE** the BB3 Finding #5 work package.
**Status of everything below:** no code was written for this proposal. The current app still uses the
deterministic regex parser exclusively. This document is evidence, not a plan of record.

---

## 1. The proposal, as Muthu put it

> "Can we not use llama 7b post paddle OCR parses the prescription to determine the time and any
> other info possible with llama 7b?"

I.e. after PaddleOCR returns raw label text, hand that text to a **local 7B** (Ollama) to extract the
medication name, dose, frequency, times, and anything else — instead of / alongside
`prescription_parser.py` + `timing_parser.py`.

### Decisions Muthu already made this session (treat as inputs, not open questions)

| Question | Muthu's answer |
|---|---|
| What should it fix? | **Both** layout long-tail *and* schedule fidelity — **ranked by measurement**, i.e. build the labelled label set first and let the failure distribution decide |
| How much authority over the profile? | **Proposer behind confirm** — explicitly: *"user should be able to review, edit and approve medications/timings in the UI"* |
| Where must it run? | Challenged the SA's premise (correctly — see §3). Left open pending measurement |
| Real-phone torch test | Deferred (unrelated, tracked separately) |

**The review/edit/approve screen is the most important product idea in this exchange** and is worth
building whether or not an LLM is ever added. It is the deterministic safety net that makes *any*
proposer — regex or model — safe, and it would have neutralised by construction every parser bug
fixed in FixbySonnet1, FixbySonnet2, and today's batch.

---

## 2. The SA's objections, and how each one actually fared

Recorded honestly because the pattern matters for the red-team: **the SA raised three objections
against the local 7B, and all three collapsed or narrowed sharply under Muthu's pushback and
measurement.** Fable should assume the remaining case is weaker than it sounds.

| # | Objection as first stated | What happened |
|---|---|---|
| 1 | "Production has no GPU — a local 7B can't run there" | **WRONG.** Production's ML tier *is* Muthu's laptop: the droplet (2 vCPU / 4 GB, no GPU) runs only backend + SPA + Postgres + nginx, and reaches the sidecar over Tailscale at `100.119.95.105:8100`. A local 7B is reachable in production exactly the way BB3 already is. |
| 2 | "VRAM contention with IMB1 on an 8 GB card" | **MEASURED AWAY.** 7B resident *plus* a live pill analysis peaks at 7,374 / 8,188 MiB. Nothing offloaded. See §3. |
| 3 | "`num_ctx` silent truncation is a safety trap" | **NARROWED to cheap-to-fix.** Measured KV slope is 0.056 MB/token, so 4k → 16k context costs only 684 MiB. Set `num_ctx=16384` and the trap closes. |

**What survives of the SA's case after measurement:** only the *quality* argument — the F9-11
celecoxib prior on this same local model, and the literature in §5. Notably, **extraction accuracy
of qwen2.5:7b on Canadian label text was never measured.** That is the decisive missing number
(§7).

---

## 3. Measured GPU/memory numbers (this session, 2026-07-28)

Hardware: **NVIDIA GeForce RTX 4060 Laptop GPU, 8,188 MiB total**; 7,957 MiB free at idle (~231 MiB
held by Windows/display). Ollama 0.31.2. Script: `scratchpad/vram_measure.py` (session scratchpad —
not in the repo; reproduce from the numbers below).

Models already pulled locally: `qwen2.5:7b-instruct` (4.7 GB), `qwen2.5:3b-instruct` (1.9 GB),
`mistral:latest` (4.4 GB), `llama3:latest` (4.7 GB). **Note: the project's "local 7B" is
qwen2.5-7b-instruct, not llama** — qwen uses GQA, which is why the KV cache is cheap.

| Measurement | Result |
|---|---|
| Sidecar fully up (`imb1_ok`, `sb2_ok`, `bb3_ok`, `ocr_worker: present`), at rest | **0 MiB** — all models lazy-loaded |
| First pill analysis (cold) | peak **1,978 MiB**, settles to **1,547 MiB resident**, **52.9 s** |
| `qwen2.5:7b-instruct` @ `num_ctx=4096` | **4,639 MiB** (ollama reports size 4,748 MB, `size_vram` 4,748 MB = **100% on GPU**), load 8.8 s |
| `qwen2.5:7b-instruct` @ `num_ctx=16384` | **5,323 MiB** (ollama size 5,465 MB, 100% on GPU), load 7.6 s |
| **KV-cache slope** | (6,870 − 6,186) MiB / 12,288 tokens = **0.056 MB/token** |
| `keep_alive: 0` | frees cleanly to 1,547 MiB in **2.6 s**, `ollama ps` shows 0 models |
| Cold reload @ `num_ctx=8192` | **7.5 s** to first response |
| Warm call (already resident) | **0.2 s** |
| **Contention case: 7B resident + live pill analysis** | before 6,414 → **peak 7,374 / 8,188 MiB** → after 6,944. **Fits.** 7B stayed at `size_vram` 4,987 MB (no CPU offload). Analysis completed in 25.6 s (warm IMB1) |

**Interpretation.** Both models coexist at ~90% card utilisation with ~814 MiB headroom, sequentially
or concurrently. If you prefer not to hold the 7B resident, `keep_alive: 0` costs **7.5 s** per Rx
scan — trivial beside OCR's own 15–22 s. **Resource capacity is not the blocker.**

### Threats to validity of these numbers (red-team should probe)
- Single run per configuration; no repeats, no variance.
- One image, one pill; a multi-pill NB08-style scene may allocate more in IMB1.
- 814 MiB headroom is thin: a larger image, a second concurrent request, or a Chrome/desktop VRAM
  spike could tip it. Nothing was measured under real concurrent load.
- PaddleOCR is compiled with CUDA (`paddle 3.3.1 compiled_with_cuda=True`) but showed **no** VRAM at
  rest; whether an active OCR call allocates GPU memory was **not** isolated (the pill-analyze path
  was measured, not the OCR path).
- `nvidia-smi` sampling was 200 ms; a shorter transient peak could have been missed.
- A probe-script defect: the script read `decision` off the `/pill/analyze` response and got `None`.
  That is a key-name mismatch in the probe, **not** an app finding. VRAM figures unaffected.

---

## 4. The deterministic baseline the LLM would have to beat

Do not let the LLM be compared against the *old* broken parser. As of this session:

- **Probe set (12 realistic Canadian label shapes, incl. 5 phantom-record traps):** **12/12 fully
  correct — 0 missed medications, 0 phantom medications.** Before this session's fixes: 8/12
  (4 missed). Probe: `scratchpad/probe_splitter.py`.
- **Live E2E through real PaddleOCR + real backend** on `archive/docs/Synthetic_Prescription_Test1.png`:
  **5 prescription records** (was 1), correct names and dosages, per-record schedules, and **5
  linkable DIN suggestions** at scores 95.0 / 85.5 / 95.0 / 89.18 / 95.0 — up from a single
  suggestion at 90.0. 201 in 14.8 s.
- **Backend suite: 127 passed.**
- Literature baseline for a *rule-based* system on this task: **MedEx F 96.0% on frequency, 93.2% on
  drug names** (§5). The regex ceiling is higher than it intuitively feels.

Known remaining regex gaps (measured, deliberately not fixed — legitimate LLM targets):
`"every N hours"` yields no frequency category; bare `"daily"` without a count word → `UNKNOWN`;
`with food` categorises but maps to no slots (rule-ordering issue, see comment in `timing_parser.py`);
a real multi-drug label with **no** enumeration and **no** per-med dosage line still collapses to one
record; PRN medications and multi-drug splitting both now behave, but nothing handles tapers or
`"1 tab AM, 2 tabs PM"`.

---

## 5. Prior art found (2026-07-28), with verification status

### 5.1 The load-bearing one — MEDIC (Amazon Pharmacy)

**"Large language models for preventing medication direction errors in online pharmacies"**, Nature
Medicine 2024. <https://pmc.ncbi.nlm.nih.gov/articles/PMC11186789/> ·
<https://www.nature.com/articles/s41591-024-02933-8>
**Status: VERIFIED by direct fetch** (see caveat below).

This is our exact task — turning raw prescriber directions into structured, safe sig lines — solved in
production at pharmacy scale. Reported architecture and results:

- **Architecture:** fine-tuned **DistilBERT for NER** (nine components: verb, dose, route, frequency,
  auxiliary) → **rule-based pharmalexical normalization** → semantic assembly → **five safety
  guardrails** → medication catalog (DMedCat) cross-check. Trained on **1,000 expert-annotated**
  directions + 10,000 synthetically augmented.
- **Results on 1,200 retrospective prescriptions:** **Claude (10-shot) produced 4.38× more near-miss
  events** (CI 3.13–6.64) than MEDIC; a **T5 fine-tuned on 1.5M samples produced 1.51× more**
  (CI 1.03–2.31). In production: **33% reduction in near-miss events** (CI 26–40%), **95.1% flagging
  accuracy** on historical errors.
- **Why the pure-LLM approaches lost:** hallucination with high confidence, dropped frequency/route,
  invented dose forms — and critically, **they continued generating when they should have abstained.**

**MEDIC's five guardrails (halt generation when):** (1) extracted components conflict with the
medication catalog; (2) multiple values detected for one component; (3) dose present without a verb;
(4) frequency component missing; (5) dose missing for a tablet/capsule formulation.

**Why this matters for PillSafe:** (a) it independently confirms our own abstain-over-guess thesis in
our exact domain, from a production deployment — a strong paper citation; (b) all five guardrails are
transplantable onto what we already have, and guardrail #1 maps directly onto the 7,055-DIN
harmonized reference; (c) the winning system uses **no generative LLM at all**.

> **Caveat for the red-team — verify this one against the primary source.** The architecture summary
> above came from a *single* automated fetch summarised by a small model. The paper's title frames it
> as an LLM paper while the summary describes DistilBERT NER + rules. That tension is exactly the
> kind of thing a summariser gets wrong. **Re-read the primary source before the paper cites it.**

### 5.2 Supporting literature

| Work | Relevance | Status |
|---|---|---|
| **Agrawal, Hegselmann, Lang, Kim, Sontag — "Large language models are few-shot clinical information extractors", EMNLP 2022.** <https://aclanthology.org/2022.emnlp-main.130/> DOI 10.18653/v1/2022.emnlp-main.130 | The general grounding that LLMs *can* do zero/few-shot clinical extraction | **VERIFIED** (authors, venue, pages 1998–2022) |
| **Xu, Stenner, Doan, Johnson, Waitman, Denny — "MedEx: a medication information extraction system for clinical narratives", JAMIA 2010;17(1):19–24, PMID 20064797.** <https://pubmed.ncbi.nlm.nih.gov/20064797/> | The **rule-based** baseline: F 93.2% drug name, 94.5% strength, 93.9% route, **96.0% frequency** | **VERIFIED** (venue, volume, pages, PMID, F-scores) |
| **"Automatic Posology Structuration: What role for LLMs?"** arXiv 2506.19525. <https://arxiv.org/pdf/2506.19525> | Directly on dosage-instruction structuring; evaluated **~7B open models** (Mistral, Phi, Gemma, BioMistral) on a **French** dataset; concluded LLMs did **not** universally beat rule-based, hybrid likely optimal. French matters for our user group | Paper exists & task confirmed; **exact numbers NOT extracted** (PDF content streams) — **UNVERIFIED numbers** |
| **"Customizing Open Source LLMs for Quantitative Medication Attribute Extraction across Heterogeneous EHR Systems"** arXiv 2510.21027 | **Qwen2.5-32B: 93.4% coverage, 93.0% exact-match.** Scale datapoint — that is **4.5× larger** than our local 7B | **UNVERIFIED** (search snippet only) |
| **"Approaches for extracting daily dosage from free-text prescription signatures…"** <https://pmc.ncbi.nlm.nih.gov/articles/PMC11700559/> | LLM vs **RxSig**; both good at daily-dose extraction, RxSig "more scalable" | **UNVERIFIED** (snippet only) |
| **Rx-LLM benchmarking suite** (medRxiv 2025.12.01.25341004) | A benchmark for safe LLM performance on medication tasks — candidate eval harness | **UNVERIFIED** (snippet only) |

### 5.3 Is the competition proprietary? — Yes, essentially all of it

- **MedSnap ID** — commercial, iPhone-only, **requires its own proprietary imaging pad**, patents
  (`US8861816` / `US9111357` / `US12038390` per ADR 2026-07-15). Cross-checks openFDA, DailyMed, NLM
  RxImage. Published eval (medRxiv 2020.05.06.20093427) is medication **authentication** (counterfeit
  detection, n=48), **not** profile verification.
  <https://www.prnewswire.com/news-releases/medsnap-id-app-launches-as-worlds-first-computer-vision-powered-prescription-medication-identification-service-214870421.html>
- **MEDIC** — Amazon Pharmacy internal production system.
- **Systematic review, mobile apps for falsified/substandard drugs** —
  <https://pmc.ncbi.nlm.nih.gov/articles/PMC7861418/>
- **Open-source side:** `MedTimer` is an open-source medication **reminder** app — no identification.
  **No open-source pill-identification equivalent was found.**

**Consequence for the paper:** the working systems in this space are closed, and MedSnap's tray is
proprietary. An open, ablated capture-tray design + open verification pipeline + Canadian DIN
grounding has a real gap to fill. This *strengthens* the existing "Verify, Don't Identify" novelty
claim and does not collide with it.

---

## 6. The SA's current recommendation (the thing to red-team)

**🟡 PARTIAL grounding for LLM-assisted sig parsing as a technique; the best-evidenced architecture
uses no generative LLM at all.**

Recommended order of work, cheapest-first:

1. **Build the review/edit/approve screen** (Muthu's own requirement). Deterministic, no model, no
   labels. Makes every downstream option safe and fixes the whole *class* of parser defects.
2. **Port MEDIC's five guardrails** over the existing regex parser, with guardrail #1 backed by the
   7,055-DIN harmonized reference. Grounded in a Nature Medicine production result; needs zero
   labels; surfaces uncertainty into the screen from step 1.
3. **Only then** consider a model, and measure it against the §4 baseline on a labelled Canadian
   label set. If a model is used, **CB4/Haiku** is the architecturally consistent choice (2026-07-14
   CB4 decision; ~0.52¢/call; F9-11 polarity passed live where the local 7B failed) — but note the
   local 7B is now *resource-viable* (§3), so this is a quality argument, not an infrastructure one.

**Non-negotiable regardless of choice:** nothing may auto-commit a drug name or a DIN. The parse feeds
`drug_name` → DIN auto-match → confirmed profile DINs → **SB2's verification ground truth**. Layer 1
(entity → Canadian DIN scoping) stays deterministic per the 2026-07-22 layered safety model.

---

## 7. Open questions for the red-team

1. **The decisive un-measured number:** what is qwen2.5:7b-instruct's actual per-field extraction
   accuracy on Canadian label text, against the §4 baseline (12/12 probe, 0 phantom)? Nothing in this
   document answers that. A ~30-minute probe over the 12 probe labels would.
2. Does MEDIC's result (4.38× more near-misses for a 10-shot frontier model) **transfer** to our
   setting, or is it specific to *generating* directions rather than *extracting* fields? Read the
   primary source (§5.1 caveat) before relying on it either way.
3. Is a **discriminative NER model** (MEDIC's DistilBERT shape) the right answer for PillSafe, given
   we have **zero** labelled Canadian labels and MEDIC needed 1,000 expert-annotated ones? What is the
   cheapest labelling scheme that avoids the **R1 self-distillation trap** (human-*confirmed* ≠
   human-*authored*: never label by accepting model output)?
4. Does the review/edit/approve screen make the LLM question **moot** for the capstone — i.e. is
   regex + guardrails + human confirmation already good enough, making an LLM pure scope risk?
5. Should the eval set be built from **real** Canadian pharmacy labels (privacy + acquisition problem)
   or synthesised label shapes (validity problem)? The current probe set is synthesised by the SA,
   which risks the same overfitting-to-own-fixture trap FixbySonnet1 fell into.
6. Where does **French** enter? The posology paper's dataset is French; our users include
   French-speaking seniors; PaddleOCR + the regex vocabulary are English-only. This is an unexamined
   hole in the current parser, independent of the LLM question.
7. Is the ~814 MiB VRAM headroom (§3) acceptable, or does NB08 multi-pill work consume it?

---

## 8. Session artifacts and pointers

| Thing | Where |
|---|---|
| Parser fixes this session (splitter, PRN, digit frequency) | `dev/backend/app/services/prescription_parser.py`, `timing_parser.py` |
| Regression tests (127 backend passed) | `dev/backend/tests/test_prescription_parser.py` |
| Splitter probe set (12 cases, incl. 5 phantom traps) | `redteam_probe_splitter.py` (this folder) — run with the backend venv |
| VRAM measurement script | `redteam_vram_measure.py` (this folder) — needs the sidecar up on 8100 + Ollama on 11434 |
| Live E2E Rx-scan script | `redteam_e2e_rx_split.py` (this folder) — logs in as the seeded `margaret@test.com` |
| Frontend fixes this session | `dev/frontend/src/i18n/index.ts` (`<html lang>`), `src/components/CameraCapture.tsx` (aspect ratio) |
| Prior batches | `FixbySonnet1.md`, `FixbySonnet2_parser.md` (this folder) |
| Architecture decisions | `Brainstorm/.claude/pillsafe-adr.md` (dev workspace, not in this repo) |
| Deploy topology (droplet + Tailscale sidecar) | `DEPLOY_GUIDE.md` (this folder), §1.3 / §2 / §3 |

The three `redteam_*.py` scripts are copied into this folder deliberately so every number in §3 and §4
is **re-runnable rather than merely asserted**. They are throwaway measurement harnesses, not app
code: nothing imports them, they are not in the test suite, and they may be deleted once the red-team
has served its purpose. `redteam_probe_splitter.py` carries the 12 label shapes, which are the part
worth keeping — the phantom-record traps in particular.
