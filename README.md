# PillSafe

**AI-powered medication safety for patients who deserve to understand their prescriptions.**

[![CI](https://github.com/SumanthReddyKConestoga/PillSafe/actions/workflows/ci.yml/badge.svg)](https://github.com/SumanthReddyKConestoga/PillSafe/actions/workflows/ci.yml)

PillSafe is a multi-modal medication analysis application built as part of the Conestoga College Graduate AI/ML program. It helps elderly, low-literacy, and visually impaired patients safely identify their medications and understand their prescription labels through camera-based scanning, plain-language guidance, and a voice assistant.

> **Decision Support Only** — PillSafe does not provide medical advice. Always confirm medication information with a licensed pharmacist or physician.

> Looking for a plain-English explanation of this project (no technical background needed)? See **[PROGRESS.md](PROGRESS.md)**.

## Table of Contents

1. [Architecture](#architecture)
2. [Tech Stack](#tech-stack)
3. [Running Locally — Step by Step](#running-locally--step-by-step)
4. [Repo & File Guide — what every file does](#repo--file-guide--what-every-file-does)
5. [API Reference](#api-reference)
6. [Environment Variables](#environment-variables)
7. [Test Suite](#test-suite)
8. [Known Limitations](#known-limitations-by-design)
9. [Legacy / Deprecated Artifacts](#legacy--deprecated-artifacts)

---

## Architecture

### System overview

```
┌────────────────────────────────────────────────────────────────────────────┐
│  BROWSER                                                                   │
│  React 18 SPA (Vite dev server on :5173, or static build on Vercel)       │
│                                                                              │
│   Public            Auth                Patient Dashboard       Admin      │
│   ───────           ─────               ─────────────────       ──────    │
│   Landing /         Login               Dashboard (schedule)    Stats      │
│   About             Register            Analyze (camera)        Users      │
│   Contact                               My Medications                     │
│                                          Profile / Safety /                │
│                                          Education / Settings              │
└───────────────────────────────┬──────────────────────────────────────────────┘
                                │  HTTP+JSON, JWT bearer token
                                │  (Vite proxies /api/* → :8000 in dev)
                                ▼
┌────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI BACKEND  (Python 3.11, async, :8000)                             │
│                                                                              │
│  routes/  →  services/  →  models/  →  SQLite (pillsafe.db)               │
│  (HTTP layer)  (business logic)  (ORM tables)                             │
│                                                                              │
│  Routers mounted in app/api/v1/router.py:                                 │
│  auth · patients · prescriptions · analyze · pill · reminders ·           │
│  instructions · scans · contact · admin · dev                             │
└───────┬───────────────────────┬──────────────────────────┬───────────────────┘
        │                       │                          │
        ▼                       ▼                          ▼
┌───────────────┐   ┌─────────────────────────┐   ┌──────────────────────────┐
│ SQLite file   │   │ Local image processing   │   │ External API (optional) │
│ pillsafe.db   │   │ (runs on this machine,   │   │ Anthropic Claude         │
│ + uploads/    │   │  no internet needed)     │   │ — only structured text  │
│ (photos,      │   │ • PaddleOCR (label text)  │   │   sent (color/shape/    │
│  contact log) │   │ • OpenCV (colour/shape)   │   │   imprint), NEVER the   │
│               │   │ • DIN lookup table        │   │   raw image             │
└───────────────┘   └─────────────────────────┘   └──────────────────────────┘
```

### How a "scan" actually flows through the system

**Scanning a prescription label** (`AnalyzePage` → "Scan Prescription" mode):
1. Browser opens the camera (`CameraCapture.tsx`) and captures a photo.
2. Photo is POSTed to `app/api/v1/routes/prescriptions.py`.
3. The route saves the image under `uploads/prescriptions/{patient_id}/`, then calls `ocr_service.py` (PaddleOCR) to read the text.
4. The raw text is passed to `prescription_parser.py`, which splits a multi-drug printout into one block per medication (looking for `RX 1` / `RX 2` / ... markers, falling back to today's single-medication behaviour if none are found), then calls `timing_parser.py` per block to turn phrases like *"three times daily with meals"* into structured time slots (`["morning","afternoon","evening"]`) and exact clock times (`["08:00","13:00","18:00"]`), and extracts dosage, food timing, purpose, and (for "as needed" medications) the safe daily maximum.
5. One `Prescription` row per medication is saved (`models/prescription.py`) and the list is returned to the browser, which redirects to **My Medications**.

**Scanning a loose pill** (`AnalyzePage` → "Scan Pill" mode):
1. Browser captures a photo and POSTs it to `app/api/v1/routes/pill.py`.
2. `pill_detection.py` runs real OpenCV math on the image (threshold → largest contour → HSV colour analysis → shape classification) to get a colour and shape.
3. `ocr_service.py` tries to read any imprint text stamped on the pill.
4. The colour/shape/imprint are looked up against the `din_pills` table (`pill_detection.lookup_din_candidates`).
5. If there are zero matches or no imprint, `claude_service.py` asks Claude for a plain-language description — sending **only** the colour/shape/imprint text, never the photo.
6. The browser then fetches the patient's active prescriptions and compares the result against them locally, showing a green / amber / red safety message.

**Hearing a medication reminder** (`ReminderAudio` component on `MyMedicationsPage`):
1. Patient picks a language (English / French / Arabic / Spanish) and presses "Hear Reminder" on a medication card.
2. Browser POSTs to `app/api/v1/routes/reminders.py`, which fills in a hardcoded per-language template with the patient's name and medication name — pure string formatting, zero external API calls.
3. The browser speaks the returned message via the Web Speech API (`SpeechSynthesisUtterance`), with `utterance.lang` set to match the chosen language (`en-CA` / `fr-CA` / `ar-SA` / `es-ES`).

**Reading the full instructions in your language** (`InstructionsPanel` component on `MyMedicationsPage`):
1. Patient picks a language and the panel POSTs the medication's already-extracted structured fields (drug name, dosage, frequency category, computed times, food flag, purpose, max daily dose) to `app/api/v1/routes/instructions.py`.
2. The route fills in localized phrase templates (en/fr/ar/es) — never a live translation of the original OCR text, since no translation API key is required — and returns one plain-language sentence, e.g. *"Take Ibuprofen 200mg at 8:00 AM, 1:00 PM and 6:00 PM, with food for joint pain."*
3. The sentence is displayed (not just spoken) in large text, right-aligned automatically for Arabic.

**Viewing the original prescription photo** (`PrescriptionImageModal` component on `MyMedicationsPage`):
1. Patient presses the image icon on a medication card.
2. The browser fetches `GET /prescriptions/{id}/image` as a blob via the authenticated Axios client (a plain `<img src="...">` can't carry the bearer token), then renders it via `URL.createObjectURL`.
3. The route checks the requesting patient owns that prescription before returning the file (`FileResponse`).

**Automatic dose reminders** (`src/lib/doseReminders.ts`, started once in `AppShell.tsx`):
1. On login, the browser asks for Notification permission once, then polls `GET /prescriptions/me` every 30 seconds.
2. For every active, non-"as needed" medication, it computes today's dose times from `specific_times` and fires a browser Notification + spoken alert exactly once per dose: 30 minutes before, and again at the dose time. Already-fired alerts are tracked in `sessionStorage` so a page refresh doesn't repeat them.
3. This only runs while the dashboard tab is open — it is not a background/push-notification system (see Known Limitations).

---

## Tech Stack

| Layer          | Technology                                                     |
|-----------------|-----------------------------------------------------------------|
| Frontend        | React 18, TypeScript, Vite, TailwindCSS v3                     |
| State mgmt      | Zustand (localStorage persistence)                              |
| Forms           | React Hook Form + Zod                                            |
| HTTP client     | Axios (silent token refresh interceptor)                        |
| i18n            | react-i18next (EN/FR)                                            |
| Backend         | FastAPI, Python 3.11, async/await throughout                     |
| ORM             | SQLAlchemy 2.x async (code-first, additive column sync on boot) |
| Auth            | JWT (HS256), bcrypt cost-12, httpOnly refresh cookie             |
| Database        | **SQLite** (dev) — no Docker, no Redis, no Postgres required     |
| OCR             | PaddleOCR (optional — installed & verified in the dev venv), regex-based timing parser |
| Pill detection  | OpenCV colour/shape math + DIN database lookup (optional)        |
| Guidance layer  | Claude API, structured attributes only, never raw images (optional) |
| Voice           | Web Speech API (`speechSynthesis`, browser-native), multilingual reminder/instruction templates (en/fr/ar/es) |
| Notifications   | Web Notification API (browser-native) — in-app, foreground-only dose reminders, no service worker/push |
| Camera          | `getUserMedia` (browser-native), file-upload fallback            |
| CI/CD           | GitHub Actions (backend pytest + frontend typecheck/build)       |
| Deploy          | Render (API) + Vercel (static frontend) — see `render.yaml` / `vercel.json` |

> No custom ML training, no FAISS, no YOLOv8, no NIH Pillbox dataset, no BioBERT. Pill detection is pure OpenCV math + PaddleOCR + a DIN lookup table, per `PILLSAFE_BUILD.md`. (There's a leftover notebook from an earlier, different approach that *did* plan to use YOLOv8 — see [Legacy / Deprecated Artifacts](#legacy--deprecated-artifacts).)

---

## Running Locally — Step by Step

### Prerequisites
- **Python 3.11** (check with `python --version`)
- **Node.js 20+** and npm (check with `node --version`)
- Git, obviously — you're reading this from a clone already.

### 1. Clone and enter the project
```bash
git clone https://github.com/SumanthReddyKConestoga/PillSafe.git
cd PillSafe
```
(If you already have it locally, just `cd` into it.)

### 2. Set up environment variables
```bash
cp .env.example .env
```
The defaults work out of the box for local development — SQLite needs no extra setup, and `LLM_API_KEY`/`OCR_PIPELINE_ENABLED` can stay blank/false until you want those optional features (see [Known Limitations](#known-limitations-by-design)).

### 3. Start the backend
```bash
cd dev/backend
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Leave this terminal running. You should see `Database ready` in the logs — a `pillsafe.db` SQLite file is created automatically next to `dev/backend/`, no database server to install.

- API base: **http://localhost:8000**
- Interactive API docs (Swagger): **http://localhost:8000/docs**
- Health check: **http://localhost:8000/health**

### 4. Start the frontend (in a *new* terminal)
```bash
cd dev/frontend
npm install
npm run dev
```
- App: **http://localhost:5173**

### 5. Create an account
Open http://localhost:5173, click **Get Started** / **Create Free Account**, and sign up like any normal app (email + password). That's a regular patient account.

### 6. (Optional) Create an admin account
Admins see platform stats and manage users, but are technically blocked from ever seeing patient medication data. To create one for testing, open Swagger (http://localhost:8000/docs) and call:
```
POST /api/v1/dev/seed-admin
{ "email": "admin@pillsafe.dev", "password": "Admin1234" }
```
Copy the `access_token` from the response, click **Authorize** at the top of the Swagger page, and paste it in. This endpoint only works when `APP_ENV=development` (the default) — it intentionally returns `404` in production and in CI.

### 7. Run the automated tests
```bash
cd dev/backend
pytest tests/ -v
```
All 24 should pass.

### 8. (Optional) Enable the heavier features
By default the app runs fully without these — prescription scanning shows realistic example text, and pill-photo scanning returns a clear "not available" message instead of crashing. To turn them on:
```bash
cd dev/backend
pip install -r requirements-optional.txt   # PaddleOCR, OpenCV, the Claude SDK
```
Then:
- Set `LLM_API_KEY=<your Anthropic key>` in `.env` to turn on AI-written pill descriptions.
- For real OCR, **don't** flip `OCR_PIPELINE_ENABLED` in the committed `.env` — it's shared with the pytest suite, and several tests use fake image bytes that assume OCR is off. Instead set it as a real process environment variable right before starting the server, so it only applies to that session:
  ```bash
  # macOS/Linux
  OCR_PIPELINE_ENABLED=true uvicorn app.main:app --reload --port 8000
  ```
  ```powershell
  # Windows PowerShell
  $env:OCR_PIPELINE_ENABLED='true'; uvicorn app.main:app --reload --port 8000
  ```
  (Environment variables always take precedence over `.env` file values, so this works without touching the committed default.) Installing PaddleOCR also transitively installs OpenCV, which means real pill colour/shape detection on `/analyze/pill` switches on too, at no extra cost.

### Troubleshooting
| Problem | Fix |
|---|---|
| `Address already in use` on port 8000 or 5173 | Something else is already running there — stop it, or run `uvicorn app.main:app --port 8001` and update `dev/frontend/vite.config.ts`'s proxy target. |
| Backend won't start, complains about `bcrypt` | This project pins `bcrypt==4.0.1` — `passlib` 1.7.4 is incompatible with bcrypt 5.x. Re-run `pip install -r requirements.txt` inside the venv. |
| `/dev/seed-admin` returns 404 | You're not running with `APP_ENV=development` (check your `.env`). This is intentional — that route is dev-only. |
| Camera doesn't open on the Analyze page | Browsers only allow camera access over `https://` or `localhost` — make sure you're on `http://localhost:5173`, not an IP address, and that you clicked "Allow" on the permission prompt. There's a file-upload fallback if the camera truly isn't available. |

---

## Repo & File Guide — what every file does

```
PillSafe_FINAL/
├── PILLSAFE_BUILD.md          The build spec this entire codebase implements, priority by priority
├── README.md                  This file — technical reference
├── PROGRESS.md                Plain-English explainer (no tech background needed)
├── render.yaml                Render.com deploy config for the backend
├── vercel.json                 Vercel deploy config for the frontend
├── .github/workflows/ci.yml   GitHub Actions: backend pytest + frontend typecheck/build
├── .env.example                Template for the root .env file
│
├── dev/backend/                ─── FastAPI application ───
│   ├── app/
│   │   ├── main.py                FastAPI app factory: creates the app, sets up CORS,
│   │   │                          Swagger docs, the /health check, and runs DB setup on startup
│   │   ├── api/
│   │   │   ├── deps.py            Shared auth dependencies: get_current_user (any logged-in
│   │   │   │                      user), get_current_admin (ADMIN only), get_current_patient
│   │   │   │                      (blocks ADMIN — used on every patient-data route)
│   │   │   └── v1/
│   │   │       ├── router.py      Wires every route file below into the app under /api/v1
│   │   │       └── routes/
│   │   │           ├── auth.py            register / login / logout / refresh / me
│   │   │           ├── patients.py        profile get/update, change password, delete account
│   │   │           ├── prescriptions.py   upload prescription photo (OCR, multi-medication aware),
│   │   │           │                      list/update/delete, serve the original photo back
│   │   │           ├── analyze.py         legacy demo pill-stub endpoint (kept, not used by UI anymore)
│   │   │           ├── pill.py            real pill photo analysis: OpenCV + OCR + DIN + Claude
│   │   │           ├── reminders.py       multilingual (en/fr/ar/es) spoken reminder text, zero external API calls
│   │   │           ├── instructions.py    multilingual (en/fr/ar/es) plain-language instruction sentence,
│   │   │           │                      built from structured fields, zero external API calls
│   │   │           ├── scans.py           read-only scan history for the Safety Records page
│   │   │           ├── contact.py         public "contact us" form submission
│   │   │           ├── admin.py           platform stats, user management, analyses audit log
│   │   │           └── dev.py             dev-only: bootstrap the first admin account
│   │   ├── core/
│   │   │   ├── config.py          All settings/feature flags, loaded from .env
│   │   │   ├── database.py        Creates the SQLite connection, creates tables on startup,
│   │   │   │                      and adds any new columns to existing tables automatically
│   │   │   └── security.py        Password hashing (bcrypt) and JWT token creation/verification
│   │   ├── models/                 (one file per database table)
│   │   │   ├── user.py            Login accounts — email, password hash, role (PATIENT/ADMIN)
│   │   │   ├── patient.py         A patient's profile info (name, DOB, language, settings)
│   │   │   ├── analysis.py        Records from the legacy /analyze demo endpoint
│   │   │   ├── prescription.py    A saved prescription: drug name, dosage, schedule, photo path
│   │   │   └── din_pill.py        Reference table of known pills (colour/shape/imprint) — empty
│   │   │                          until real Health Canada data is loaded, see Known Limitations
│   │   ├── schemas/                 (request/response shapes, validated automatically by FastAPI)
│   │   │   ├── auth.py · patient.py · prescription.py · scan.py · admin.py
│   │   └── services/                (the actual business logic, called by the routes above)
│   │       ├── auth_service.py        register/login logic
│   │       ├── patient_service.py     profile read/update logic
│   │       ├── prescription_service.py listing/updating/soft-deleting prescriptions
│   │       ├── prescription_parser.py splits one OCR'd photo into one or more medications
│   │       │                         (drug name, dosage, food/purpose/max-dose) before timing_parser
│   │       ├── timing_parser.py       turns text like "twice daily" into ["morning","evening"],
│   │       │                         plus classify_frequency() (QID/TID/BID/PRN/...) for instructions.py
│   │       ├── ocr_service.py         wraps PaddleOCR to read text out of a photo
│   │       ├── pill_detection.py      OpenCV colour/shape detection + DIN table lookup
│   │       ├── claude_service.py      asks Claude for a plain-language pill description
│   │       └── admin_service.py       stats/user-management logic for admins
│   ├── tests/                     pytest test suite (40 tests) — see Test Suite below
│   ├── requirements.txt           Core dependencies — installed on every deploy
│   ├── requirements-optional.txt  PaddleOCR / OpenCV / Claude SDK — install only if you want them
│   └── pillsafe.db                The actual SQLite database file (created automatically, gitignored)
│
└── dev/frontend/                ─── React application ───
    └── src/
        ├── main.tsx                   Entry point — mounts the React app into the page
        ├── App.tsx                    Top-level component, renders the router
        ├── router/index.tsx           Every page route + who's allowed to see it
        │                              (RequireAuth / RequireGuest / RequireAdmin guards)
        ├── api/                        One file per backend feature — each just wraps an HTTP call
        │   ├── client.ts              Shared Axios instance: attaches the login token to every
        │   │                          request, auto-refreshes it silently when it expires
        │   ├── auth.ts · admin.ts · patients.ts · prescriptions.ts · pill.ts · reminders.ts ·
        │   │   instructions.ts · scans.ts · contact.ts
        ├── components/
        │   ├── CameraCapture.tsx      Reusable camera viewfinder + capture/retake/confirm,
        │   │                          falls back to a file picker if the camera is denied
        │   ├── ReminderAudio.tsx      Language picker + "Hear Reminder" button on each medication
        │   │                          card — calls /reminders/message, speaks it via SpeechSynthesisUtterance
        │   ├── InstructionsPanel.tsx  Language picker that displays (not just speaks) a full
        │   │                          plain-language instruction sentence in large text
        │   ├── PrescriptionImageModal.tsx  Fetches the original prescription photo as a blob
        │   │                          (authenticated) and shows it in a modal
        │   ├── DisclaimerModal.tsx    The "this isn't medical advice" pop-up
        │   ├── layout/
        │   │   ├── AppShell.tsx       Wraps every logged-in page: sidebar + top bar + content
        │   │   ├── PublicLayout.tsx   Wraps Landing/About/Contact: simple header + footer
        │   │   ├── Sidebar.tsx        Left-hand navigation menu
        │   │   └── Topbar.tsx         Top bar: page title, language switch, voice toggle, avatar
        │   └── ui/                     Small reusable building blocks
        │       ├── Button.tsx · Card.tsx · Input.tsx · Alert.tsx · LanguageSwitcher.tsx
        ├── hooks/
        │   ├── useAuth.ts             Login/register/logout actions
        │   └── useVoicePageAnnounce.ts Announces the page name out loud on page load
        ├── lib/
        │   ├── voiceAssistant.ts      The "read it out loud" engine (browser's built-in voice)
        │   └── doseReminders.ts       Polls active prescriptions every 30s; fires a Notification +
        │                              spoken alert 30 min before and at each dose time (foreground only)
        ├── i18n/                       English/French text, and the library that switches between them
        ├── store/authStore.ts          Remembers who's logged in (persisted in the browser)
        ├── styles/globals.css          The light colour theme and text sizing rules
        ├── types/index.ts              Shared TypeScript shape definitions (what a Prescription
        │                              object looks like, etc.)
        └── pages/
            ├── public/                 No login required
            │   ├── LandingPage.tsx        The "/" homepage
            │   ├── AboutPage.tsx          "/about"
            │   └── ContactPage.tsx        "/contact"
            ├── auth/
            │   ├── LoginPage.tsx · RegisterPage.tsx
            ├── dashboard/                Everything behind login
            │   ├── DashboardPage.tsx      Home screen — today's schedule, quick actions
            │   ├── AnalyzePage.tsx        The camera page — scan a prescription OR a pill
            │   ├── MyMedicationsPage.tsx  List of everything currently being tracked
            │   ├── ProfilePage.tsx        Edit profile, change password
            │   ├── SafetyRecordsPage.tsx  History of past scans
            │   ├── EducationPage.tsx      How-to guide, safety tips, FAQ (static content)
            │   └── SettingsPage.tsx       Notifications, voice, language, delete account
            ├── admin/
            │   ├── AdminDashboardPage.tsx · AdminUsersPage.tsx
            └── NotFoundPage.tsx           Catch-all 404 page
```

---

## API Reference

All endpoints are under `/api/v1/`. Protected routes require `Authorization: Bearer <access_token>`. Full interactive docs at `/docs`.

### Auth — `app/api/v1/routes/auth.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | No | Create patient account, return token pair |
| POST | `/auth/login` | No | Validate credentials, return token pair |
| POST | `/auth/logout` | No | Clears refresh cookie |
| POST | `/auth/refresh` | Cookie | Issue new access token |
| GET | `/auth/me` | Bearer | Current user profile |

### Patients — `app/api/v1/routes/patients.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET / PATCH | `/patients/me` | Bearer | Get/update patient profile |
| PATCH | `/patients/me/password` | Bearer (patient) | Change password |
| DELETE | `/patients/me` | Bearer (patient) | Permanently delete own account |

### Prescriptions — `app/api/v1/routes/prescriptions.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/prescriptions` | Bearer (patient) | Upload prescription photo → OCR → split into one or more medications → save. Returns a **list** of prescriptions (usually 1, but more if the photo has several Rx blocks) |
| GET | `/prescriptions/me` | Bearer (patient) | List active prescriptions |
| GET | `/prescriptions/{id}/image` | Bearer (patient, owner only) | Return the original uploaded photo for that prescription |
| PATCH | `/prescriptions/{id}` | Bearer (patient) | Update a prescription |
| DELETE | `/prescriptions/{id}` | Bearer (patient) | Soft-delete a prescription |

### Analyze / Pill — `app/api/v1/routes/analyze.py`, `pill.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/analyze` | Bearer | Legacy pill-stub demo (kept for compatibility, superseded by `/analyze/pill` in the UI) |
| GET | `/analyze/history` / `/analyze/{id}` | Bearer | Legacy demo history |
| POST | `/analyze/pill` | Bearer (patient) | OpenCV colour/shape + PaddleOCR imprint + DIN candidates + Claude guidance |

### Reminders — `app/api/v1/routes/reminders.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/reminders/message` | Bearer (patient) | Returns a spoken-aloud reminder message for a medication, in English, French, Arabic, or Spanish — hardcoded templates, zero external API calls |

### Instructions — `app/api/v1/routes/instructions.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/instructions/message` | Bearer (patient) | Returns a full plain-language instruction sentence (dose, times, food, purpose, max daily dose) for a medication, in English, French, Arabic, or Spanish — built from structured fields via hardcoded templates, zero external API calls |

### Scans — `app/api/v1/routes/scans.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/scans/me` | Bearer (patient) | Safety Records — past scans with prescription match status |

### Contact — `app/api/v1/routes/contact.py`
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/contact` | No | Public contact form submission |

### Admin — `app/api/v1/routes/admin.py` (ADMIN role only)
| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/admin/stats` | Bearer + ADMIN | Platform-wide stats |
| GET | `/admin/users` / `/admin/users/{id}` | Bearer + ADMIN | List/view users |
| PUT | `/admin/users/{id}/activate` / `/deactivate` | Bearer + ADMIN | Enable/disable a user |
| PUT | `/admin/users/{id}/role` | Bearer + ADMIN | Change a user's role |
| DELETE | `/admin/users/{id}` | Bearer + ADMIN | Delete a user |
| GET | `/admin/analyses` | Bearer + ADMIN | Audit log of legacy `/analyze` records |

### Dev — `app/api/v1/routes/dev.py` (404 outside `APP_ENV=development`)
| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/dev/seed-admin` | No | Bootstrap the first admin account |

**Admins are blocked (403, not just 404) from every patient-data endpoint** — `/prescriptions/*`, `/scans/*`, `/patients/me/password` — enforced by the `get_current_patient` dependency in `app/api/deps.py`, regardless of how the request is made.

**Error envelope** — all errors use this shape:
```json
{ "detail": { "error": { "code": "EMAIL_TAKEN", "message": "An account with this email already exists.", "details": {} } } }
```

---

## Environment Variables (`.env` at project root)

| Variable | Description | Example |
|---|---|---|
| `APP_ENV` | `development` / `production` / `test` | `development` |
| `SECRET_KEY` | JWT signing secret — change in prod | `openssl rand -hex 32` |
| `DATABASE_URL` | SQLAlchemy async connection string | `sqlite+aiosqlite:///./pillsafe.db` |
| `FRONTEND_ORIGIN` | Allowed CORS origin | `http://localhost:5173` |
| `OPENAPI_ENABLED` | Expose `/docs` and `/redoc` | `true` |
| `ML_PIPELINE_ENABLED` | Gate for the legacy `/analyze` real pipeline | `false` |
| `OCR_PIPELINE_ENABLED` | Gate for real PaddleOCR on `/prescriptions` | `false` |
| `LLM_API_KEY` | Anthropic API key — blank keeps guidance inert | *(blank until you add one)* |
| `LLM_MODEL` | Claude model id | `claude-sonnet-4-6` |
| `UPLOAD_DIR` | Where prescription images / contact log are written | `./uploads` |

> **Note on `OCR_PIPELINE_ENABLED`:** this `.env` is read by both the running app *and* the pytest suite (`tests/test_prescriptions.py` assumes it's `false`). Keep it `false` here; flip it via a real process env var instead when you want real OCR for a one-off run — see step 8 in [Running Locally](#running-locally--step-by-step).

---

## Test Suite

```bash
cd dev/backend && pytest tests/ -v
```
40 tests covering auth, patients (password change, self-delete), prescriptions (CRUD, ownership, admin-block, graceful degradation on bad uploads, multi-medication creation, image retrieval), the multi-medication OCR parser in isolation (`test_prescription_parser.py` — letterhead exclusion, dosage extraction, PRN vs scheduled, max-daily-dose), pill analysis (graceful degradation without OpenCV, mocked happy path), reminders and instructions (auth guard, per-language templates, unknown-language fallback), scans, and the contact form. CI runs the same suite with `APP_ENV=test` on every push to `main` — see the badge at the top of this file.

---

## Known Limitations (by design)

- **DIN database is empty.** `din_pills` table exists with the right schema/indices but has no seed data — pill-mode scans will show "no matches found" until a real Health Canada DPD extract is loaded. See `app/models/din_pill.py`.
- **PaddleOCR / OpenCV are not installed by default.** `/prescriptions` falls back to demo OCR text and `/analyze/pill` returns a clear `501 CV_UNAVAILABLE` until `requirements-optional.txt` is installed. (They are installed and verified working in this project's `dev/backend/venv` — see step 8 above for how to switch `OCR_PIPELINE_ENABLED` on for a single session without touching the committed `.env`.)
- **Claude guidance is inert without an API key.** No raw images or PHI are ever sent — only structured colour/shape/imprint attributes, per the Data Privacy rule in `PILLSAFE_BUILD.md`.
- **Dose reminders are in-app/foreground-only.** `doseReminders.ts` polls and fires Notification + voice alerts only while the dashboard tab is open in the browser; it is not a background push-notification system (no service worker, no VAPID keys, no backend scheduler) — that would be a separate, larger feature.
- **Instruction sentences are template-based, not a live translation.** `instructions.py` builds French/Arabic/Spanish sentences from structured fields (dose, time, food, purpose) already extracted by `prescription_parser.py`, rather than translating the OCR'd text word-for-word — this keeps it deterministic and free of any external translation API dependency.

For the full plain-language breakdown of what's done and what's left, see **[PROGRESS.md](PROGRESS.md)**.

---

## Legacy / Deprecated Artifacts

Three files at the project root predate `PILLSAFE_BUILD.md` and are **not used anywhere in the current app**:

| File | What it is | Why it's unused |
|---|---|---|
| `orchestrator.ipynb` | A Jupyter notebook stub outlining a 5-step ML pipeline: data collection → preprocessing → train a **YOLOv8** segmentation model → evaluate → export. Every cell just prints `[STUB] ...` — no real code ever ran. | `PILLSAFE_BUILD.md` explicitly replaced this approach: *"NO custom ML training. NO YOLOv8 custom training. NO NIH Pillbox image dataset."* Pill detection now uses OpenCV math instead (`app/services/pill_detection.py`). |
| `data-collection/collect_pillbox.py` | A script intended to download the NIH Pillbox image dataset for training that YOLOv8 model. | Same reason — the NIH Pillbox dataset approach was explicitly ruled out in favour of OpenCV + a DIN reference table. |
| `training/trained-model-v0.h5` | A placeholder/empty model weights file from the same earlier approach. | Never trained on real data; superseded the same way. |

They were left in place rather than deleted, since deleting files is a one-way action and wasn't asked for — but they no longer reflect the direction of the project and can be safely archived or removed whenever you're ready.

---

## Contributing

**Branch naming:** `feat/<short-description>` · `fix/<issue>` · `chore/<task>`

**Commit messages:** [Conventional Commits](https://www.conventionalcommits.org/)

---

*PillSafe · Conestoga College Graduate AI/ML Program · AIML-6900 Capstone*
