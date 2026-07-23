# MyPillSafe

**Scan a pill before you take it. Understand your medication in your own language.**

[![CI](https://github.com/muthuacumen/mypillsafe/actions/workflows/ci.yml/badge.svg)](https://github.com/muthuacumen/mypillsafe/actions/workflows/ci.yml)

MyPillSafe is the application surface of **PillSafe**, a medication-safety capstone project
(Conestoga College Graduate AI/ML program, AIML-6900). It is built for **seniors and people
in Canada facing language barriers** who manage multiple medications:

- **Scan a prescription label** → the app reads it, proposes the matching Canadian DIN
  (Drug Identification Number), and builds a medication + schedule profile — the patient
  always confirms, nothing is auto-committed.
- **Photograph a loose pill** → the app checks it **against that patient's own confirmed
  medications** and answers *verify*, *reject*, or *abstain* — it warns when a pill does
  not match anything the patient should be taking, and says "I'm not sure" rather than guess.
- **Ask about a medication** → answers are generated only from the official Canadian
  product monograph of the resolved drug, with citations, in the user's language (EN/FR).

> **Decision-support only — not medical advice.** MyPillSafe never replaces a pharmacist
> or physician. Every decision-bearing screen carries this disclaimer. This is a capstone
> MVP, not a licensed medical device.

---

## Table of Contents

1. [The Five-Brain Architecture](#the-five-brain-architecture)
2. [Design Principles](#design-principles)
3. [Repository Layout](#repository-layout)
4. [Running Locally](#running-locally)
5. [Environment Variables & Feature Flags](#environment-variables--feature-flags)
6. [API Overview](#api-overview)
7. [Test Suite & CI](#test-suite--ci)
8. [Docker & Cloud Deploy](#docker--cloud-deploy)
9. [Known Limitations](#known-limitations-by-design)
10. [Research Grounding](#research-grounding)
11. [Team](#team)

---

## The Five-Brain Architecture

PillSafe is organized as five cooperating "brains". Three of them are **frozen, separately
tested Python packages** that live *outside* this repository and are served to the app by a
local sidecar microservice; the other two live inside the app itself.

| Brain | What it does | Where it lives |
|---|---|---|
| **OB5** — OCR brain | Reads a prescription label photo (PaddleOCR) → drug name, dosage, schedule → proposes DIN matches for the patient to confirm | App backend (`dev/backend`) |
| **IMB1** — pill image brain | Photographs a loose pill → colour, shape, type, and a dual-read of any imprint | Frozen package `IMB1_v0/` (sibling of the repo parent), via the brains sidecar |
| **SB2** — matcher brain | Deterministic, auditable scorer: compares the pill record against the patient's confirmed DINs → **verify / reject / abstain** | Frozen package `SB2/`, via the brains sidecar |
| **BB3** — monograph Q&A brain | Resolves the drug being asked about, retrieves *only that drug's* monograph passages, applies deterministic safety guards, and assembles cited context | Frozen package `BB3/`, via the brains sidecar |
| **CB4** — cloud voice | The only cloud component: a Claude model turns BB3's guarded, cited context into a plain-language answer in the user's language; its output is re-checked by BB3's guards | App backend (`app/services/cb4_service.py`) |

```
┌──────────────────────────────────────────────────────────────────────────┐
│  BROWSER — React 18 SPA + PWA (Vite :5173)                               │
│  Public: Landing · About chain (Vision/Problem/Science/Team) · Contact   │
│          + floating MyPillSafe Assistant (project explainer, EN/FR,      │
│            voice input; medication questions redirect to guarded Q&A)    │
│  Patient: Dashboard · Scan Prescription · Scan Pill · My Medications ·   │
│           Ask (Q&A) · Scan History · Help · Profile · Settings           │
│  Admin:   Stats · Users                                                  │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │ HTTP+JSON, JWT bearer
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  APP BACKEND — FastAPI (:8000) · SQLite · uploads/                       │
│                                                                          │
│  OB5: PaddleOCR label reading → prescription parser → DIN suggestions    │
│  CB4: Claude (LLM_API_KEY) speaks BB3's cited context — the ONLY         │
│       cloud call in the system; raw images are never sent anywhere       │
└───────────────┬──────────────────────────────────────────────────────────┘
                │ HTTP (127.0.0.1:8100)
                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  BRAINS SIDECAR — FastAPI (dev/brains, :8100), own Python 3.12 venv      │
│  Hosts the frozen packages (imported from sibling folders, local-only):  │
│    IMB1_v0  → /pill/analyze     (detect → colour/shape/type/imprint)     │
│    SB2      → verify/reject/abstain vs the patient's confirmed DINs      │
│    BB3      → /qa/chat context + /qa/guard (resolver-scoped retrieval,   │
│               deterministic guards, cited monograph context)             │
│  No cloud keys here by design. GPU (CUDA) stays on the host.             │
└──────────────────────────────────────────────────────────────────────────┘
```

**Why "verify, don't identify"?** Identifying an arbitrary pill from the full Canadian
formulary is not reliably solvable from a phone photo — many marketed products look
identical. Verifying a pill **against the handful of medications a patient is actually
prescribed** is a much smaller, safer question, and it allows the honest third answer:
*abstain* ("I can't tell — check with your pharmacist"), which the system prefers over
guessing. The same philosophy scopes Q&A: the BB3 resolver is the **only door** to drug
information — retrieval is always scoped to one resolved drug's monograph, never a
free-text search across all drugs, and dosing questions are refused outright.

---

## Design Principles

- **Abstain over guess.** Every decision path has a built-in "I'm not sure" outcome, and
  it is treated as a first-class result, never an error.
- **Deterministic guards around the model.** LLM output is checked by rule-based guards
  (drug-entity match, ingredient consistency, dosing refusal); the guards are code, not
  another model's opinion.
- **The cloud sees text, never photos.** CB4 receives structured, cited monograph context.
  Pill and prescription images are processed locally.
- **Disclaimers are mandatory** on every decision-bearing surface, and the decision colour
  tokens (`success`/`warning`/`danger`) are frozen — abstain (amber) is never rendered as
  verified (green) or rejected (red).
- **No fabricated claims.** App copy carries no invented statistics, testimonials, or
  certifications; performance figures live in the research documentation, not in the app.

---

## Repository Layout

```
PillSafe/                        (this repo — app layer only)
├── README.md                    This file
├── Makefile                     Docker + local-dev targets
├── render.yaml · vercel.json    Optional app-only cloud deploy (see Docker & Cloud Deploy)
├── .env.example                 Template for the root .env
├── .github/workflows/ci.yml     CI: backend pytest + frontend type-check/build
├── docker/                      docker-compose stack + nginx config
├── documentation/
│   └── integration/             App×brains integration plan, phase results,
│                                LOCAL_TESTING.md (launch guide + seeded test accounts)
├── dev/backend/                 FastAPI app — auth, patients, prescriptions (OB5 OCR +
│                                DIN linking), pill-scan proxy, Q&A (CB4), assistant,
│                                reminders/instructions, scans, admin
├── dev/brains/                  Brains sidecar (FastAPI :8100) — serves the frozen
│                                IMB1_v0 / SB2 / BB3 packages to the app
└── dev/frontend/                React 18 + TypeScript + Tailwind SPA, PWA-enabled

# NOT in this repo (frozen research packages, siblings of the repo's parent folder):
# D:\Projects\PillSafe\IMB1_v0\   pill image pipeline
# D:\Projects\PillSafe\SB2\       deterministic matcher + Canadian appearance reference
# D:\Projects\PillSafe\BB3\       monograph retrieval + guards (multi-GB local store)
# Each has its own CONTRACT.md — those contracts are authoritative for integration.
```

---

## Running Locally

### Prerequisites

- **Python 3.11+** (CI runs 3.11; 3.12 is what the dev machine uses)
- **Node.js 20+** and npm
- For the full pill-scan and Q&A experience: the three frozen brain packages
  (`IMB1_v0`, `SB2`, `BB3`) installed as siblings of this repo's parent folder, an
  NVIDIA GPU for the sidecar, and a Python 3.12 venv in `dev/brains/.venv`
  (`pip install -r dev/brains/requirements.txt`). Package roots can be overridden with
  the `IMB1_ROOT` / `SB2_ROOT` / `BB3_ROOT` environment variables.

**Without the brain packages the app still runs** — accounts, prescription scanning
(with OCR), reminders, instructions, and the public site all work; pill analysis and
monograph Q&A report the sidecar as unavailable instead of crashing.

### 1. Environment

```powershell
copy .env.example .env
```
Defaults work out of the box. Add an Anthropic key as `LLM_API_KEY` to enable CB4
(generated Q&A and assistant answers); without a key those paths fall back or degrade
gracefully.

### 2. Brains sidecar (Terminal 1, optional but recommended, :8100)

```powershell
cd dev\brains
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
```
First start takes a while (loads the appearance reference and opens the BB3 store).
Check <http://127.0.0.1:8100/health>.

### 3. App backend (Terminal 2, :8000)

```powershell
cd dev\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-optional.txt   # PaddleOCR (Rx scanning), Claude SDK, voice STT
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
API docs: <http://127.0.0.1:8000/docs> · Health: <http://127.0.0.1:8000/health>

### 4. Frontend (Terminal 3, :5173)

```powershell
cd dev\frontend
npm install
npm run dev
```
Open **<http://localhost:5173>**. Chrome's address-bar install icon installs the PWA
(localhost counts as a secure origin).

### Test accounts & guided test flows

See **[documentation/integration/LOCAL_TESTING.md](documentation/integration/LOCAL_TESTING.md)**
for five pre-seeded patient accounts (each with three confirmed real OTC medications),
suggested end-to-end flows (pill verify/reject/abstain, Q&A with citations, assistant
widget, French paths), and expected timing behaviour.

Useful to know:

- The **first pill analysis is slow** (model load + a fresh OCR subprocess per call — a
  deliberate process-isolation constraint); later calls are faster but still take seconds.
- A full prescription-label OCR pass on CPU can take a couple of minutes — the UI shows
  progress states.
- Don't run Ollama during pill analysis (GPU contention); it is only used by the
  offline-fallback Q&A voice, never by the CB4 path.
- To create an admin account, use `POST /api/v1/dev/seed-admin` from Swagger — it only
  exists when `APP_ENV=development`.

---

## Environment Variables & Feature Flags

Defined in `dev/backend/app/core/config.py`, loaded from `.env` (see `.env.example`).

| Variable | Purpose | Default |
|---|---|---|
| `APP_ENV` | `development` / `production` / `test` (gates `/dev/*` routes) | `development` |
| `SECRET_KEY` | JWT signing secret — change in production | dev placeholder |
| `DATABASE_URL` | SQLAlchemy async URL | SQLite `pillsafe.db` |
| `FRONTEND_ORIGIN` | CORS origin | `http://localhost:5173` |
| `OPENAPI_ENABLED` | Expose `/docs` | `true` |
| `OCR_PIPELINE_ENABLED` | Real PaddleOCR on prescription upload (off = demo text) | `true` |
| `LLM_API_KEY` | Anthropic key — enables CB4; blank = offline fallback / degraded | *(blank)* |
| `LLM_MODEL` | Claude model for CB4 | `claude-haiku-4-5` |
| `BRAINS_SERVICE_URL` | Where the sidecar listens | `http://127.0.0.1:8100` |
| `PILL_V2_ENABLED` | Kill-switch for the pill-scan path (sidecar-backed; there is no other pill path) | `true` |
| `UPLOAD_DIR` | Prescription photos / contact log | `./uploads` |

Sidecar-side: `IMB1_ROOT`, `SB2_ROOT`, `BB3_ROOT` (frozen-package locations), `BRAINS_PORT`.

---

## API Overview

All app endpoints live under `/api/v1/` (interactive docs at `/docs`). Protected routes
take `Authorization: Bearer <token>`. Errors use one envelope:
`{"detail": {"error": {"code": ..., "message": ..., "details": {}}}}`.

| Area | Endpoints | Notes |
|---|---|---|
| Auth | `POST /auth/register` · `/auth/login` · `/auth/logout` · `/auth/refresh` · `GET /auth/me` | JWT + httpOnly refresh cookie |
| Patients | `GET/PATCH /patients/me` · `PATCH /patients/me/password` · `DELETE /patients/me` | Admins are blocked from patient data |
| Prescriptions (OB5) | `POST /prescriptions` (photo → OCR → one row per medication, **with DIN suggestions**) · `GET /prescriptions/me` · `GET /prescriptions/{id}/image` · `PATCH /prescriptions/{id}` (incl. DIN confirm/unset) · `DELETE /prescriptions/{id}` | DINs are suggested, never auto-committed |
| Reference | `GET /reference/search` | Authenticated proxy to the sidecar's DIN name search |
| Pill scan | `POST /analyze/pill/v2` | The only pill endpoint: sidecar IMB1→SB2, returns verify/reject/abstain + per-attribute breakdown + disclaimer; empty profile short-circuits |
| Q&A (BB3→CB4) | `POST /qa/chat` | Resolver statuses (confirm, pick-list, refusals) surface as real UI flows; answers cite DIN-scoped monograph sections |
| Assistant | `POST /assistant/chat` · `POST /assistant/voice` | Public project-explainer widget (KB + CB4, EN/FR, speech-to-text); medication questions are redirected to the guarded Q&A |
| Reminders / Instructions | `POST /reminders/message` · `POST /instructions/message` | Template-based, en/fr/ar/es, zero external calls |
| Scans | `GET /scans/me` | Safety Records history (verify/reject/abstain per scan) |
| Contact | `POST /contact` | Public form |
| Admin | `/admin/stats` · `/admin/users*` · `/admin/analyses` | ADMIN role only |

Brains sidecar (`:8100`, local-only, no auth — never expose beyond localhost):
`GET /health` · `POST /pill/analyze` · `GET /reference/search` · `GET /reference/candidates` ·
`POST /qa/chat` (context mode for CB4, full mode for the offline fallback) · `POST /qa/guard`
(runs BB3's deterministic guards over CB4's answer).

---

## Test Suite & CI

```powershell
cd dev\backend
venv\Scripts\python.exe -m pytest tests/ -v
```

The backend suite covers auth, patients, prescriptions (incl. multi-medication OCR
parsing and DIN suggestion/confirmation), the pill-scan proxy (flag off/on, sidecar-down
degradation, empty-profile short-circuit), Q&A (CB4 called/mocked, guard retry, offline
fallback), the assistant (intent gate, confidence zones, rate limiting), reminders,
instructions, scans, contact, and admin.

CI (GitHub Actions) runs the backend suite plus frontend `type-check` and `build` on
every push to `main`. The brains sidecar has its own smoke test
(`dev/brains/smoke_test.py`) which requires the frozen packages and is run locally, not
in CI.

---

## Docker & Cloud Deploy

**Docker (local):** `make dev` brings up the app stack via `docker/docker-compose.yml`.
The **brains sidecar intentionally stays on the host** (not containerized): it needs the
host GPU/CUDA, imports the frozen packages from sibling folders outside the repo, and
BB3's multi-gigabyte store must never be copied into an image. The compose file maps
`host.docker.internal` so the containerized backend reaches the host-run sidecar; see the
comments in `docker/docker-compose.yml`.

**Cloud (optional, app-only demo):** `render.yaml` (backend) and `vercel.json` (frontend)
deploy the app **without the brains** — accounts, prescription OCR, reminders,
instructions, and the public site work; pill verification and monograph Q&A are
unavailable there because the sidecar and its GPU-backed frozen packages are local-only
by design. Treat a cloud deploy as a shareable demo of the app shell, not the full
five-brain system.

---

## Known Limitations (by design)

- **This is a capstone MVP under active research.** The pill pipeline's accuracy figures
  come from a small development set; the confirmatory capture campaign (a controlled
  tray + phone-flash protocol) is still ahead. No performance claims are made in the app,
  and none should be quoted from it.
- **Abstain is common.** The matcher is tuned to keep false-accepts rare, at the cost of
  frequently answering "I can't tell — check with your pharmacist." That trade-off is
  deliberate and should not be "fixed" by loosening thresholds.
- **The frozen brain packages are not in this repo.** Pill verification and monograph
  Q&A require them (plus a GPU) on the machine running the sidecar.
- **Q&A refuses dosing questions** and drug-vs-drug comparisons; brands absent from the
  Canadian formulary get an explicit "not in the Canadian formulary" refusal rather than
  a guess.
- **Dose reminders are foreground-only** (browser Notification + speech while the tab is
  open) — there is no push-notification backend.
- **Instruction sentences are template-based** (en/fr/ar/es) built from structured fields,
  not live translation of the OCR text.
- **PWA install needs HTTPS** off localhost; camera access likewise.

---

## Research Grounding

The pill-verification approach ("verify against the patient's own medications, with an
explicit abstain") and the monograph-scoped Q&A design are grounded in published work on
pill recognition and its limits — see the in-app **Scientific Foundation** page
(`/about/science`) for the cited papers with links. A research paper on the pill pipeline
(working title *"Verify, Don't Identify"*) is in preparation; its evidence and numbers
live with the frozen research packages and their contracts, not in this repo.

---

## Team

**MyPillSafe · 2026** — Muthuraj Jayakumar · Sumanth Reddy · Lohith Reddy · Ali Ozdemir ·
Abdullah Mohammed

Roles and per-member responsibilities: see `/about/team` in the app.

**Contributing:** branch as `feat/<desc>` / `fix/<issue>` / `chore/<task>`; commits follow
[Conventional Commits](https://www.conventionalcommits.org/).

---

*PillSafe · Conestoga College Graduate AI/ML Program · AIML-6900 Capstone · Decision-support only — not medical advice.*
