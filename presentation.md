# PillSafe — Complete Project Flow, Architecture & Data Reference

*A full technical walkthrough of everything built so far: every database table, every model, every pipeline, and exactly how data moves from a phone camera to the screen and back. Written to be presentable as-is.*

---

## 1. What PillSafe Is

PillSafe is a medication-safety web app for elderly patients, caregivers, and low-vision users. It does three things:

1. **Reads a prescription label photo** and turns it into structured, scheduled medication records (name, dose, exact times, food instructions).
2. **Identifies a loose, unlabeled pill** from a photo (colour + shape + any imprint) and checks it against the patient's actual prescriptions.
3. **Speaks and displays everything in plain language**, in English, French, Arabic, or Spanish, with proactive reminders — built for someone who may not read small print or a second language well.

It is explicitly a **decision-support tool, not medical advice** — every result screen carries that disclaimer.

---

## 2. High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│  BROWSER — React 18 SPA (Vite dev server :5173)                                  │
│                                                                                    │
│  Public          Auth              Patient Dashboard (behind login)      Admin    │
│  ──────          ────             ─────────────────────────────────     ─────    │
│  Landing         Login            Dashboard (next dose + schedule)      Stats     │
│  About           Register         Analyze (camera: Rx or pill)          Users     │
│  Contact                          My Medications (view/listen/read)               │
│                                    Profile · Safety Records · Education ·          │
│                                    Settings                                        │
└───────────────────────────────────┬────────────────────────────────────────────────┘
                                    │ HTTP + JSON over Axios
                                    │ Authorization: Bearer <JWT access token>
                                    │ httpOnly refresh_token cookie (auto-silent-refresh)
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────────┐
│  FASTAPI BACKEND — Python 3.11, fully async (uvicorn :8000)                       │
│                                                                                    │
│   routes/  (HTTP layer, FastAPI routers)                                          │
│        │                                                                          │
│        ▼                                                                          │
│   services/ (business logic — parsing, auth, OCR wrapper, OpenCV wrapper)         │
│        │                                                                          │
│        ▼                                                                          │
│   models/ (SQLAlchemy ORM tables)  ──────────────────►  SQLite (pillsafe.db)      │
│                                                                                    │
│   11 routers mounted in app/api/v1/router.py:                                     │
│   auth · patients · analyze · pill · prescriptions · reminders · instructions ·   │
│   scans · contact · admin · dev                                                   │
└───────┬─────────────────────────┬──────────────────────────────┬──────────────────┘
        │                         │                              │
        ▼                         ▼                              ▼
┌────────────────┐   ┌─────────────────────────────┐   ┌──────────────────────────┐
│ SQLite file    │   │ Local, on-machine processing │   │ External API (optional) │
│ pillsafe.db    │   │ (no internet required)       │   │ Anthropic Claude        │
│ + uploads/     │   │ • PaddleOCR — reads text      │   │ structured attributes  │
│   (prescription│   │   out of a photo              │   │ ONLY (colour/shape/    │
│   photos)      │   │ • OpenCV — colour + shape math│   │ imprint) — NEVER the   │
│                │   │ • regex frequency parser      │   │ raw photo               │
└────────────────┘   └─────────────────────────────┘   └──────────────────────────┘
```

**Why this shape:** every "smart" capability (OCR, colour/shape detection, AI guidance) is a swappable, optional local module behind a feature flag. If it's not installed or not configured, the route degrades to safe demo data or a clear error instead of crashing — the app is always usable end-to-end even with zero ML dependencies installed.

---

## 3. Database Schema — Complete

**Engine:** SQLite (file `dev/backend/pillsafe.db`), accessed via SQLAlchemy 2.x **async** ORM (`aiosqlite` driver). No Docker, no Postgres, no Redis required for development.

**Schema management:** Code-first, **not** Alembic (Alembic is scaffolded in `migrations/` but unused). On every app startup (`app/core/database.py`):
1. `Base.metadata.create_all()` creates any tables that don't exist yet.
2. `_add_missing_columns()` runs hand-written `ALTER TABLE ... ADD COLUMN` statements for any column added to a model *after* the table already existed on disk — this is how the project evolves the schema without a migration tool, checking `PRAGMA table_info(table)` first so it's idempotent.

### 3.1 `users` — login identity

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID4 |
| `email` | VARCHAR(255) UNIQUE, indexed | |
| `hashed_password` | VARCHAR(255) | bcrypt, cost factor 12 |
| `role` | VARCHAR(20) | `"PATIENT"` or `"ADMIN"` |
| `is_active` | BOOLEAN | soft-disable a login without deleting it |
| `is_verified` | BOOLEAN | reserved, not currently enforced anywhere |
| `created_at` / `updated_at` | DATETIME | server-side defaults |

Relationships: **1-to-1** with `patients` (cascade delete), **1-to-many** with `analyses` (cascade delete).

### 3.2 `patients` — profile data, one per patient user

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID4 — this is the ID used everywhere else as `patient_id` |
| `user_id` | VARCHAR(36) FK → `users.id`, UNIQUE | enforces exactly one patient profile per login |
| `first_name`, `last_name` | VARCHAR(100) | |
| `date_of_birth` | DATE | |
| `preferred_language` | VARCHAR(10), default `"en"` | static UI language (i18next) |
| `phone_number` | VARCHAR(20), nullable | |
| `medications_analyzed` | INTEGER, default 0 | incremented by the legacy `/analyze` flow |
| `last_scan_at` | DATETIME, nullable | |
| `notifications_enabled` | BOOLEAN, default true | toggle in Settings |
| `is_active` | BOOLEAN | |
| `created_at` / `updated_at` | DATETIME | |

Relationships: belongs to one `user`; has many `prescriptions` (cascade delete — deleting the account wipes all medication data).

### 3.3 `prescriptions` — one row per *medication* (not per photo)

This is the most important table — it's the one that changed shape this round to support multi-medication photos.

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | UUID4 |
| `patient_id` | VARCHAR(36) FK → `patients.id`, indexed | |
| `drug_name` | VARCHAR(255) | e.g. `"Ibuprofen"` |
| `dosage` | VARCHAR(100), nullable | e.g. `"200mg"` |
| `frequency_text` | VARCHAR(255), nullable | the medication's own instruction sentence, e.g. *"Take 1-2 tablets THREE TIMES DAILY with meals... take with food"* |
| `frequency_type` | VARCHAR(30), nullable | one of `QID` / `TID` / `BID` / `BEDTIME` / `WITH_MEALS` / `ONCE_DAILY` / `PRN` / `UNKNOWN` |
| `time_slots` | JSON (list) | coarse day-parts, e.g. `["morning","afternoon","evening"]` |
| `specific_times` | JSON (list) | exact 24h clock times, e.g. `["08:00","13:00","18:00"]` — empty for PRN |
| `with_food` | BOOLEAN, default false | |
| `purpose` | VARCHAR(100), nullable | e.g. `"joint pain"` |
| `max_daily_dose` | INTEGER, nullable | e.g. `8` (tablets/24h) — only meaningful for PRN |
| `prescribing_doctor` | VARCHAR(255), nullable | not currently populated by the parser |
| `refills_remaining` | INTEGER, nullable | not currently populated by the parser |
| `expiry_date` | DATE, nullable | |
| `is_active` | BOOLEAN, default true | **soft delete** — "removing" a medication just flips this to false, the row is never hard-deleted |
| `image_path` | VARCHAR(500), nullable | filesystem path to the original uploaded photo |
| `created_at` / `updated_at` | DATETIME | |

**Key design point:** one uploaded photo → **one row per detected medication**, all sharing the same `image_path`. A 3-drug pharmacy printout produces 3 rows, not one — see §5 for exactly how that split happens.

### 3.4 `analyses` — legacy pill-scan history (also feeds Safety Records)

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `user_id` | VARCHAR(36) FK → `users.id`, indexed | |
| `status` | VARCHAR(20), default `"completed"` | |
| `image_filename` | VARCHAR(255), nullable | filename only — the legacy `/analyze` endpoint never saves the actual file |
| `pills_detected` | JSON (list) | |
| `label_info` | JSON (dict) | `{drug_name, dosage, frequency, ...}` |
| `guidance` | TEXT, nullable | |
| `safety_alerts` | JSON (list) | |
| `ml_pipeline_enabled` | BOOLEAN | |
| `created_at` | DATETIME | |

This table predates `pill.py`'s real OpenCV pipeline; it's kept for the legacy `/analyze` demo endpoint and is what `GET /scans/me` (Safety Records page) reads from.

### 3.5 `din_pills` — Health Canada reference table for pill identification

| Column | Type | Notes |
|---|---|---|
| `id` | VARCHAR(36) PK | |
| `din` | VARCHAR(20), indexed | Health Canada Drug Identification Number |
| `product` | VARCHAR(255) | brand/product name |
| `active_ingredient`, `strength` | VARCHAR, nullable | |
| `colour`, `shape` | VARCHAR(50), indexed, nullable | matched against OpenCV's output |
| `scoring`, `coating` | VARCHAR(50), nullable | |
| `imprint` | VARCHAR(100), indexed, nullable | matched against OCR'd imprint text |
| `confidence` | FLOAT, default 1.0 | ranking weight |

**Currently empty.** The schema and lookup logic are fully built (`pill_detection.lookup_din_candidates`) but no real Health Canada DPD data extract has been loaded — pill scans always return "no database matches," falling through to the Claude-guidance fallback (or a "consult your pharmacist" message if Claude isn't configured).

### 3.6 Entity-relationship summary

```
users (1) ──── (1) patients (1) ──── (many) prescriptions
  │                                        all share image_path per upload batch
  └──── (many) analyses

din_pills — standalone reference table, queried by colour+shape+imprint, not FK-linked
```

---

## 4. Authentication & Security

- **Password hashing:** bcrypt via `passlib`, cost factor baked into the `bcrypt==4.0.1` pin (a newer `bcrypt` 5.x breaks `passlib` 1.7.4's API, so this version is deliberately pinned).
- **Tokens:** two JWTs (HS256, signed with `SECRET_KEY`):
  - **Access token** — `{sub: user_id, role, type: "access"}`, 60-minute expiry, sent as `Authorization: Bearer <token>` on every request, kept in `localStorage` on the frontend.
  - **Refresh token** — `{sub: user_id, type: "refresh"}`, 7-day expiry, stored as an **httpOnly** cookie (`refresh_token`, path-scoped to `/api/v1/auth/refresh` only) — never readable by JavaScript, so it can't be stolen via XSS.
- **Silent refresh:** the frontend's Axios client (`src/api/client.ts`) auto-attaches the access token to every request. On a `401`, it calls `POST /auth/refresh` (which reads the httpOnly cookie), gets a new access token, and retries the original request transparently — the user never sees a forced logout unless the refresh token itself has expired. Concurrent 401s from multiple components share **one** in-flight refresh call (fixed this round — previously each component fired its own redundant refresh request).
- **RBAC:** two roles, `PATIENT` and `ADMIN`. Three FastAPI dependencies in `app/api/deps.py`:
  - `get_current_user` — any valid token.
  - `get_current_admin` — `ADMIN` role only (403 otherwise).
  - `get_current_patient` — **blocks `ADMIN`** (403) — used on every single patient-PHI route (`/prescriptions/*`, `/scans/*`, `/patients/me/password`, `/reminders/*`, `/instructions/*`). This is enforced in code, not just policy — an admin's JWT will get a 403 even if they craft the request by hand.
- **CORS:** locked to the known frontend origins (`localhost:5173`/`5174` + configured `FRONTEND_ORIGIN`).
- **Data-privacy rule (enforced in code, not just policy):** `claude_service.py` only ever sends structured attributes (colour, shape, imprint text, DIN candidates) to the Anthropic API — the raw photo is never transmitted off the machine.

---

## 5. The Prescription-Reading Pipeline — Full Detail

This is the "model used for reading the prescription." There is **no trained ML model** here — by deliberate design (`PILLSAFE_BUILD.md` explicitly rules out custom ML training) it's a combination of an off-the-shelf OCR engine plus a hand-written, deterministic text parser. Every step:

### Step 1 — Capture (frontend)
`CameraCapture.tsx` opens `navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })`, draws the live video frame to a `<canvas>`, and calls `canvas.toBlob(..., 'image/jpeg', 0.92)` to get a JPEG `Blob`. If the camera is denied/unavailable, it swaps to a plain `<input type="file" accept="image/*">` — same downstream code path either way.

### Step 2 — Upload (frontend → backend)
`prescriptionsApi.upload(blob)` wraps the blob in `FormData` and `POST`s to `/api/v1/prescriptions`.

### Step 3 — Save the photo (backend, `prescriptions.py`)
The route reads the raw bytes, writes them to `uploads/prescriptions/{patient_id}/{uuid}.{ext}` on local disk, and remembers that path — every medication parsed out of this photo will share this exact `image_path`.

### Step 4 — OCR: photo → raw text (`ocr_service.py`)
```python
def extract_text(image_bytes: bytes) -> str:
    engine = _get_engine()           # lazy-loaded PaddleOCR(use_angle_cls=True, lang="en")
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    result = engine.ocr(np.array(image), cls=True)
    return "\n".join(line for page in result for detection in page for line in [detection[1][0]] if line)
```
- **Model used:** [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) (`paddleocr==2.9.1` / `paddlepaddle==2.6.2`) — a pre-trained, general-purpose text-detection-and-recognition model (PP-OCR), used entirely out-of-the-box. No fine-tuning, no custom training.
- The engine is loaded **once** (module-level singleton behind a `threading.Lock`) and reused for every request after that.
- **Gated by `OCR_PIPELINE_ENABLED`.** When `false` (the committed default, and what CI/pytest always runs with), the route skips OCR entirely and uses a hardcoded demo string instead — so the whole app, including the test suite, works with zero ML dependencies installed.
- **Runs off the event loop.** This was a real bug fixed this round: OCR inference takes 10–40+ seconds and is fully synchronous/CPU-bound; calling it directly inside an `async def` route froze the *entire* server (every other user's request) for that whole duration. It's now wrapped in `fastapi.concurrency.run_in_threadpool`.
- **Failure handling:** `OcrUnavailableError` (package not installed) or any other exception (corrupt/non-image upload) both fall back to the same demo text rather than crashing the request — confirmed by a real test that uploads a plain `.txt` file disguised as an image and still gets `201`.

### Step 5 — Split one photo into N medications (`prescription_parser.py`, new this round)
A single pharmacy printout often lists several drugs at once. The raw OCR text (one long string, line-by-line in reading order) is split on lines that look like `RX 1`, `RX 2`, etc.:
```python
_RX_MARKER = re.compile(r"^\s*RX\s*\d+\s*$", re.I | re.M)
```
- If markers are found, the text **between** consecutive markers becomes one block per medication.
- If **no** markers are found (e.g. the OCR-disabled demo text, or a differently-formatted label), it falls back to the original single-medication behaviour — so this is purely additive, nothing regresses.
- Per block, regexes pull out:
  - **Dosage**: `r"(\d+(?:\.\d+)?\s*(?:mg|mcg|ml|g|iu))"` — drug name is everything before that match, with any `(Brand Name)` parenthetical stripped.
  - **Food timing**: `r"\bwith (meals?|food)\b"` → boolean.
  - **Max daily dose** (for PRN drugs): `r"(?:do not exceed|maximum|max)\s+(\d+)\s*(?:tablets?|...)"`.
  - **Purpose**: `r"\bfor\s+([a-z ]{1,40}?)(?=[.,;:\n—-]|$)"` — e.g. *"for joint pain"* → `"joint pain"`.
  - Everything from the line `Qty:` onward is discarded (refill counts, DIN, prescriber signature block never pollute the instruction text).

### Step 6 — Frequency classification (`timing_parser.py`)
Two parallel, regex-rule-based functions read the per-medication instruction sentence:
```python
_PHRASE_RULES = [QID, TID, BID, BEDTIME, WITH_MEALS, ONCE_DAILY, bare morning/afternoon/evening]
_CATEGORY_RULES = [same categories, used to tag frequency_type]
_PRN_PATTERN = r"\bas\s+needed\b|\bprn\b"   # checked first, highest priority
```
- `classify_frequency()` returns a single tag (`PRN`, `TID`, `ONCE_DAILY`, ...) used later for both storage and choosing the right instruction-sentence template.
- `parse_time_slots()` / `parse_specific_times()` turn the same text into coarse day-parts and any literal clock times mentioned (`"8am"` → `"08:00"`).
- **PRN medications get *no* fixed schedule at all** (`time_slots = []`, `specific_times = []`) — clinically, "take as needed" has no fixed time, so it's deliberately excluded from the dashboard's chronological schedule and from the reminder engine, and shown instead as a distinct "As needed · max N/24h" badge.
- For everything else, if no literal clock time was found in the text, a default mapping fills in real times so the dashboard always has something concrete to show:
  ```python
  {"morning": "08:00", "afternoon": "13:00", "evening": "18:00", "night": "21:00"}
  ```

### Step 7 — Persist (one `INSERT` for all medications)
The route builds one `Prescription` ORM object per parsed medication (all pointing at the same `image_path`) and `db.add_all()` + `flush()`s them in a single transaction. The response is a **list** of `PrescriptionOut` objects — this was a breaking-but-deliberate change from the old single-object response, with the frontend (`AnalyzePage.tsx`, `prescriptions.ts`) updated to match.

### Verified, real-world example
Uploading the actual demo prescription photo (Conestoga Medical Centre letterhead, three Rx blocks) through this exact pipeline produces:

| drug_name | dosage | frequency_type | specific_times | with_food | purpose | max_daily_dose |
|---|---|---|---|---|---|---|
| Acetaminophen | 500mg | PRN | `[]` | false | pain or fever | 8 |
| Ibuprofen | 200mg | TID | `["08:00","13:00","18:00"]` | true | joint pain | — |
| Loratadine | 10mg | ONCE_DAILY | `["08:00"]` | false | seasonal allergie* | — |

*(OCR misread "allergies." as "allergie:." — a real, acknowledged OCR artifact, not a parser bug.)*

The clinic letterhead ("CONESTOGA MEDICAL CENTRE") never appears as a drug name — it sits *before* the first `RX 1` marker and is structurally excluded from every block.

### Step 8 — Viewing the photo back
`GET /prescriptions/{id}/image` returns the saved file via `FileResponse`, after verifying the requesting patient actually owns that prescription (`prescription_service.get_owned`). The frontend can't use a plain `<img src="...">` here (no way to attach the auth header to an `<img>` tag), so `PrescriptionImageModal.tsx` fetches it as a `blob` via the authenticated Axios client and renders it with `URL.createObjectURL`.

---

## 6. The Pill-Identification Pipeline (loose pill photo → match)

A second, independent pipeline for the "I found a loose pill, what is it?" flow (`POST /analyze/pill` in `pill.py`):

1. **Colour + shape** (`pill_detection.py`, pure OpenCV math, *not* a trained model):
   - Grayscale → Gaussian blur → Otsu threshold → largest external contour (the pill itself, isolated from the background).
   - Mean HSV colour inside that contour, bucketed into named colours (`red`, `orange`, `yellow`, `green`, `blue`, `pink`, `white`, `beige`) by hue/saturation/value ranges.
   - Shape from contour geometry: circularity, aspect ratio, and solidity (vs. convex hull) distinguish `round` / `oval` / `oblong` / `capsule` / `square`.
2. **Imprint text** — the *same* `ocr_service.extract_text()` used for prescriptions, run on the pill photo, best-effort (any failure just means "no imprint detected," never aborts the scan).
3. **DIN lookup** — `lookup_din_candidates()` queries the (currently empty) `din_pills` table by colour + shape (+ imprint if found), ordered by confidence, top 5.
4. **Claude guidance fallback** — if there are zero DIN matches or no imprint, and `LLM_API_KEY` is set, `claude_service.py` sends **only** `{color, shape, imprint, candidates}` (never the photo) to Claude for a short plain-language description. Inert (`None`) without a key.
5. **Client-side safety check** (`AnalyzePage.tsx`) — the browser fetches the patient's own active prescriptions and locally string-matches the detected candidate names against them, showing green ("matches your prescription") or red ("does not match — do not take without consulting a pharmacist").

Both the colour/shape detection and the imprint OCR are wrapped in `run_in_threadpool` for the same event-loop-blocking reason as §5.

---

## 7. Multilingual & Audio System — Full Detail

There is **no speech-to-text or text-to-speech model running on the server.** All audio is the browser's own built-in [Web Speech API](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisUtterance) (`speechSynthesis`) — zero cost, zero external API calls, works offline. The backend's job is only to generate the *text* to speak, in the right language.

### 7.1 The voice-assistant singleton (`src/lib/voiceAssistant.ts`)
A small observer-pattern class, used everywhere "read this out loud" happens:
```ts
class VoiceAssistant {
  isEnabled() / toggle() / subscribe(fn) / speak(text) / stop()
}
export const voice = new VoiceAssistant();   // one shared instance
```
- Setting persisted in `localStorage`.
- `speak()` no-ops silently if the user has voice turned off, or if `speechSynthesis` doesn't exist in the browser.
- Used for page-load announcements (`useVoicePageAnnounce` hook — "Dashboard page loaded."), dashboard greetings, scan-result announcements, and dose reminders.

### 7.2 Two *separate* text-generation systems, both server-side, both template-based (no LLM)

**(a) Short spoken reminders** — `POST /reminders/message` (`reminders.py`):
```python
_TEMPLATES = {
  "en": "Hi {name}, according to your prescription, it's time to take {medication}. Please take it as directed by your doctor.",
  "fr": "Bonjour {name}, selon votre ordonnance, il est temps de prendre {medication}. ...",
  "ar": "مرحباً {name}، وفقاً لوصفتك الطبية، حان وقت تناول {medication}. ...",
  "es": "Hola {name}, según su receta médica, es hora de tomar {medication}. ...",
}
```
Driven by the **"Hear Reminder"** button (`ReminderAudio.tsx`) on every medication card — picks a language, fetches the message, speaks it via `new SpeechSynthesisUtterance(message)` with `utterance.lang` set to the matching BCP-47 code (`en-CA`/`fr-CA`/`ar-SA`/`es-ES`) so the browser's TTS voice/accent matches.

**(b) Full plain-language instructions** — `POST /instructions/message` (`instructions.py`, new this round):
A richer template set covering dose, exact times, food, purpose, and PRN max-dose, built from the **structured fields already extracted in §5** — never a live translation of the raw OCR text (deliberate: no translation API is configured, and translating arbitrary freeform OCR output reliably would require one). Two base templates (`scheduled` vs `PRN`) per language, with composable clauses:
```python
_SCHEDULED = {"en": "Take {drug}{dosage} at {times}{food}{purpose}.", "fr": "Prenez {drug}{dosage} à {times}{food}{purpose}.", "ar": "...", "es": "..."}
_PRN       = {"en": "Take {drug}{dosage} as needed{purpose}{max}.", ...}
_FOOD = {"en": ", with food", ...}      # appended only if with_food=True
_PURPOSE = {"en": " for {p}", ...}      # appended only if purpose is set
_MAX = {"en": ". Do not take more than {n} in 24 hours", ...}   # appended only for PRN with a known max
```
Real verified output for the Ibuprofen example above:
| Language | Generated sentence |
|---|---|
| English | *"Take Ibuprofen 200mg at 8:00 AM, 1:00 PM and 6:00 PM, with food for joint pain."* |
| Arabic | *"تناول Ibuprofen 200mg في 8:00 AM, 1:00 PM و 6:00 PM، مع الطعام من أجل joint pain."* |
| Spanish (PRN example) | *"Tome Acetaminophen 500mg cuando sea necesario para pain or fever. No tome más de 8 en 24 horas."* |

This text is **displayed**, not just spoken — `InstructionsPanel.tsx` renders it in large (`text-xl font-semibold`) text for elderly readability, automatically setting `dir="rtl"` for Arabic.

### 7.3 The proactive dose-reminder engine (`src/lib/doseReminders.ts`, new this round)
The only piece of the audio system that runs **without** the user pressing a button:
1. Starts once per login (mounted in `AppShell.tsx`, which wraps every authenticated page), requests `Notification.requestPermission()` once.
2. Polls `GET /prescriptions/me` every 30 seconds.
3. For every active, non-PRN medication, computes today's dose datetimes from `specific_times`, and for each one schedules two alert moments: 30 minutes before, and at the exact time.
4. When "now" crosses an alert moment it hasn't fired yet (tracked in `sessionStorage` so a page refresh doesn't repeat it), it fires a browser `Notification` *and* calls `voice.speak(...)`.
5. **Scope limitation, by deliberate decision:** this only works while the dashboard tab is open in the browser. True background push notifications (working even with the app fully closed) would need a service worker + VAPID keys + a server-side push scheduler — a much larger build that was explicitly scoped out given timeline, after presenting the trade-off directly to the user.

### 7.4 Static UI translation (separate, smaller system)
`react-i18next` + JSON locale files (`src/i18n/locales/en.json`, `fr.json` — **only** these two exist) handle fixed interface strings (nav labels, button text) via `t('dashboard.greeting')`. This is unrelated to the dynamic, per-medication multilingual systems in §7.2 — those go through the backend template endpoints instead, since the content is patient-specific and not a static string.

---

## 8. Frontend Architecture

- **Routing** (`src/router/index.tsx`, React Router v6, `createBrowserRouter`): three guard components — `RequireAuth`, `RequireGuest`, `RequireAdmin` — gate every route based on Zustand store state (`isAuthenticated`, `user.role`).
- **State management** (Zustand, `src/store/authStore.ts`): a tiny persisted store holding just `{ user, isAuthenticated }`; the actual JWT lives in `localStorage` directly (`access_token` key), separate from the Zustand-persisted slice.
- **API layer** (`src/api/`): one file per backend feature (`auth.ts`, `patients.ts`, `prescriptions.ts`, `pill.ts`, `reminders.ts`, `instructions.ts`, `scans.ts`, `contact.ts`, `admin.ts`), each just a thin wrapper over a shared `client.ts` Axios instance.
- **`client.ts`** — the one place all auth machinery lives: request interceptor attaches the bearer token; response interceptor catches `401`, de-duplicates concurrent refresh attempts into a single shared in-flight promise, retries the original request, or redirects to `/login` if the refresh itself fails.
- **Pages** (`src/pages/dashboard/`): `DashboardPage` (next-dose hero + chronological schedule), `AnalyzePage` (camera, both Rx and pill modes), `MyMedicationsPage` (list + image viewer + instructions panel + reminder audio), `ProfilePage`, `SafetyRecordsPage`, `EducationPage`, `SettingsPage`.
- **Styling**: TailwindCSS v3, a light, high-contrast theme with deliberately larger base font size and big tap targets, defined once in `globals.css` and `tailwind.config.ts` (`slot-badge-*`, `badge`, `card`, `stat-card` utility classes reused everywhere).

---

## 9. End-to-End Data Flow — Every Major Journey

### Journey A — Sign up & first login
```
Browser: RegisterPage form → authApi.register()
Backend: POST /auth/register → auth_service.register_user()
         → INSERT users row (bcrypt-hashed password)
         → INSERT patients row (same transaction)
         → issue access_token (60min) + refresh_token (7d, httpOnly cookie)
Browser: store access_token in localStorage → GET /auth/me → store user in Zustand
         → navigate to /dashboard
```

### Journey B — Scan a multi-drug prescription photo
```
Browser: CameraCapture → JPEG Blob → prescriptionsApi.upload(blob)
Backend: POST /prescriptions
   1. save photo to uploads/prescriptions/{patient_id}/{uuid}.jpg
   2. run_in_threadpool(ocr_service.extract_text) → raw multi-line text
   3. prescription_parser.parse_medications(raw_text)
        → split on "RX n" markers → per-block regex extraction
        → timing_parser.classify_frequency() + parse_frequency() per block
   4. build N Prescription ORM rows, same image_path, db.add_all() + flush()
   5. return list[PrescriptionOut]  (HTTP 201)
Browser: AnalyzePage shows one card per medication → "View My Medications"
```

### Journey C — Dashboard load
```
Browser: DashboardPage mount → prescriptionsApi.listMine()
Backend: GET /prescriptions/me → WHERE patient_id=? AND is_active=1, newest first
Browser: buildTodaysDoses() flattens every prescription's specific_times into
         {drug, time, label} rows, sorted chronologically (PRN rows excluded —
         empty specific_times) → findNextDose() picks the soonest →
         render "Next dose" hero + chronological list, re-ticking every 30s
         for a live countdown
```

### Journey D — Reading instructions in your language
```
Browser: InstructionsPanel → user picks "Français" →
         instructionsApi.getMessage({drug_name, dosage, frequency_type,
                                      specific_times, with_food, purpose,
                                      max_daily_dose, language: "fr"})
Backend: POST /instructions/message → fill localized template → return sentence
Browser: render sentence in large text (RTL if Arabic) — no speech yet
         (separate "Hear Reminder" button drives speechSynthesis instead)
```

### Journey E — Proactive reminder (no user action)
```
Browser (background, while app open): doseReminders.ts tick() every 30s
   → GET /prescriptions/me → compute today's (dose_time - 30min) and dose_time
     moments for every scheduled (non-PRN) medication
   → if now has crossed an unfired moment:
        new Notification("PillSafe", {body: "..."})  +  voice.speak("...")
        mark fired in sessionStorage (no repeat on refresh)
```

### Journey F — Scan a loose pill
```
Browser: CameraCapture → pillApi.analyze(blob)
Backend: POST /analyze/pill
   1. run_in_threadpool(pill_detection.detect_color_and_shape) → (colour, shape)
   2. run_in_threadpool(ocr_service.extract_text) → imprint (best-effort)
   3. pill_detection.lookup_din_candidates(colour, shape, imprint) → din_pills query
   4. if no candidates or no imprint: claude_service.generate_pill_guidance(
        colour, shape, imprint, candidates)   # structured data only, no photo
   5. return {detected_color, detected_shape, detected_imprint, candidates,
              claude_description}
Browser: fetch own active prescriptions → local string-match the candidate
         product names → green "matches" / red "does not match, consult a
         pharmacist" → optional within-schedule-window check via specific_times
```

### Journey G — Admin viewing platform stats (and what they *can't* see)
```
Admin browser: AdminDashboardPage → adminApi.stats() / adminApi.listUsers()
Backend: GET /admin/stats, GET /admin/users — requires get_current_admin
If that same admin's token hits GET /prescriptions/me or /scans/me:
   get_current_patient dependency explicitly rejects role=="ADMIN" → 403,
   regardless of how the request is crafted — this is a code-level
   guarantee, not a UI-only restriction.
```

---

## 10. Complete API Reference

All under `/api/v1`, JSON in/out, Bearer auth unless noted. Interactive docs at `/docs`.

| Router | Method & Path | Auth | What it does |
|---|---|---|---|
| auth | POST `/auth/register` | — | Create patient + user, return token pair |
| auth | POST `/auth/login` | — | Validate credentials, return token pair |
| auth | POST `/auth/logout` | — | Clear refresh cookie |
| auth | POST `/auth/refresh` | refresh cookie | Issue new access+refresh token pair |
| auth | GET `/auth/me` | Bearer | Current user + patient profile summary |
| patients | GET/PATCH `/patients/me` | Bearer | Read/update profile |
| patients | PATCH `/patients/me/password` | Bearer, patient | Change password |
| patients | DELETE `/patients/me` | Bearer, patient | Hard-delete account (cascades everything) |
| prescriptions | POST `/prescriptions` | Bearer, patient | Upload photo → OCR → multi-med parse → save. Returns **list** |
| prescriptions | GET `/prescriptions/me` | Bearer, patient | List active prescriptions |
| prescriptions | GET `/prescriptions/{id}/image` | Bearer, patient, owner | Return the original photo |
| prescriptions | PATCH/DELETE `/prescriptions/{id}` | Bearer, patient, owner | Update / soft-delete |
| analyze | POST `/analyze` | Bearer | Legacy demo pill-stub (kept for compatibility) |
| analyze | GET `/analyze/history`, `/analyze/{id}` | Bearer | Legacy demo history |
| pill | POST `/analyze/pill` | Bearer, patient | Real OpenCV + OCR + DIN + Claude pill analysis |
| reminders | POST `/reminders/message` | Bearer, patient | Short spoken reminder, en/fr/ar/es |
| instructions | POST `/instructions/message` | Bearer, patient | Full plain-language instruction sentence, en/fr/ar/es |
| scans | GET `/scans/me` | Bearer, patient | Past scan history + prescription match status |
| contact | POST `/contact` | — | Public contact-form submission |
| admin | GET `/admin/stats` | Bearer, admin | Platform-wide counts |
| admin | GET `/admin/users`, `/admin/users/{id}` | Bearer, admin | List/view users |
| admin | PUT `/admin/users/{id}/activate`/`deactivate` | Bearer, admin | Enable/disable a login |
| admin | PUT `/admin/users/{id}/role` | Bearer, admin | Change role |
| admin | DELETE `/admin/users/{id}` | Bearer, admin | Delete a user |
| admin | GET `/admin/analyses` | Bearer, admin | Audit log of legacy `/analyze` records |
| dev | POST `/dev/seed-admin` | — (404 outside dev) | Bootstrap the first admin account |

Error shape, everywhere: `{"detail": {"error": {"code": "...", "message": "..."}}}`.

---

## 11. Tech Stack at a Glance

| Layer | Technology | Notes |
|---|---|---|
| Frontend framework | React 18 + TypeScript + Vite | |
| Styling | TailwindCSS v3 | light theme, large text, big tap targets |
| State | Zustand (+ localStorage persistence) | |
| Forms | React Hook Form + Zod | |
| HTTP | Axios | shared client, silent token refresh |
| Static i18n | react-i18next | EN/FR UI strings only |
| Backend framework | FastAPI (Python 3.11, fully async) | |
| ORM | SQLAlchemy 2.x async | code-first, additive column sync |
| Auth | JWT (HS256) + bcrypt cost-12 + httpOnly refresh cookie | |
| Database | SQLite (`aiosqlite`) | swappable to Postgres (`asyncpg` already a dependency) |
| OCR | PaddleOCR (pre-trained, no fine-tuning) | optional, gated by `OCR_PIPELINE_ENABLED` |
| Pill colour/shape | OpenCV (pure image-processing math) | optional, gated by package presence |
| AI guidance | Anthropic Claude API | optional, inert without `LLM_API_KEY` |
| Voice | Web Speech API (`speechSynthesis`) | browser-native, zero cost |
| Notifications | Web Notification API | browser-native, foreground-only |
| Camera | `getUserMedia` | file-upload fallback |
| Testing | pytest + pytest-asyncio + httpx (backend), `tsc --noEmit` (frontend) | 40 backend tests |
| CI/CD | GitHub Actions | pytest + frontend typecheck/build on every push |
| Deploy targets | Render (API) + Vercel (static frontend) | `render.yaml` / `vercel.json` |

**Explicitly not used, by design:** no custom-trained ML model, no YOLOv8, no FAISS, no BioBERT, no NIH Pillbox dataset. Everything "smart" is either a pre-trained off-the-shelf tool (PaddleOCR) or deterministic math/regex (OpenCV contour analysis, the frequency parser).

---

## 12. Repository Layout (high-level)

```
PillSafe_FINAL/
├── README.md, PROGRESS.md, presentation.md   ← documentation (technical / plain-English / this file)
├── PILLSAFE_BUILD.md                         ← the original build spec this implements
├── dev/backend/app/
│   ├── main.py                  FastAPI app factory, CORS, lifespan (DB init), /health
│   ├── api/
│   │   ├── deps.py              get_current_user / get_current_admin / get_current_patient
│   │   └── v1/router.py + routes/*.py   (11 routers, listed in §10)
│   ├── core/  config.py · database.py · security.py
│   ├── models/  user · patient · prescription · analysis · din_pill
│   ├── schemas/ (Pydantic request/response shapes, one file per feature)
│   └── services/
│       ├── auth_service · patient_service · prescription_service · admin_service
│       ├── timing_parser.py         frequency text → time slots / classification
│       ├── prescription_parser.py   one photo → N structured medications
│       ├── ocr_service.py           PaddleOCR wrapper
│       ├── pill_detection.py        OpenCV colour/shape + DIN lookup
│       └── claude_service.py        structured-attributes-only AI guidance
├── dev/backend/tests/   40 pytest tests
└── dev/frontend/src/
    ├── router/, store/, hooks/, i18n/
    ├── api/          one thin wrapper per backend feature + client.ts (auth/refresh)
    ├── lib/           voiceAssistant.ts · doseReminders.ts
    ├── components/    CameraCapture · ReminderAudio · InstructionsPanel ·
    │                  PrescriptionImageModal · DisclaimerModal · layout/ · ui/
    └── pages/         public/ · auth/ · dashboard/ · admin/
```

---

## 13. Test Coverage

40 backend tests (`pytest`), covering:
- Auth (register/login/refresh/logout, password rules, self-delete)
- Prescriptions: CRUD, ownership enforcement, admin-block, graceful degradation on a corrupt/non-image upload, **multi-medication creation from one photo**, image retrieval
- The OCR text parser **in isolation** (`test_prescription_parser.py`) — letterhead never becomes a drug name, dosage/food/purpose/max-dose extraction, PRN vs. scheduled distinction, fallback behaviour with no Rx markers
- Pill analysis: graceful 501 without OpenCV, mocked happy path
- Reminders and instructions: auth guard, per-language templates, unknown-language fallback
- Scans, contact form

Frontend: `tsc --noEmit` — zero TypeScript errors across the whole app (the closest thing to a frontend test suite currently in place; no unit/component tests yet).

---

## 14. Known Limitations (honest, by design or not-yet-done)

- **`din_pills` is empty** — pill scans never get a real database match until a Health Canada DPD data extract is loaded.
- **Claude guidance is inert without a paid API key** — by design, no raw image ever leaves the machine either way.
- **Dose reminders are foreground-only** — no service worker / push infrastructure yet; works only while the app tab is open.
- **Instruction sentences are template-built from extracted fields, not a literal translation** of the original prescription wording — a deliberate trade-off to avoid depending on an unconfigured translation API.
- **OCR's accuracy depends on the multi-Rx marker format** (`RX 1`, `RX 2`, ...) for the multi-medication split; a differently-formatted label without those markers falls back to single-medication parsing (the pre-existing behaviour), which can still mis-take a letterhead as the drug name on an unfamiliar template.
- **Static UI is only translated to English/French** — the dynamic multilingual systems (§7.2) cover all 4 languages; the surrounding nav/button labels do not yet.

---

*PillSafe · Conestoga College Graduate AI/ML Program · AIML-6900 Capstone*
