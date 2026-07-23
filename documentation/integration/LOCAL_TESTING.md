# MyPillSafe — Local Launch & Test Guide

Written at Phase 5 SA verification (2026-07-19). For Muthu's independent testing of the
integrated app (Phases 1–5). Phase 6 will fold this into the main README/run story.

## 1. Launch (three terminals, in this order)

All commands are PowerShell, from the repo root `D:\Projects\PillSafe\PillSafe`.

**Terminal 1 — brains sidecar (IMB1 + SB2 + BB3, port 8100):**
```powershell
cd dev\brains
.\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
```
Wait until it logs "Application startup complete" (~30–60 s: loads the 7,055-row
reference + opens the BB3 store). Check: <http://127.0.0.1:8100/health> should show
`"imb1_ok": true, "sb2_ok": true, "bb3_ok": true`.

**Terminal 2 — app backend (port 8000):**
```powershell
cd dev\backend
.\venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Check: <http://127.0.0.1:8000/health> → `{"status":"ok"}`. API docs: <http://127.0.0.1:8000/docs>.

**Terminal 3 — frontend (port 5173):**
```powershell
cd dev\frontend
npm run dev
```

**Open the app: <http://localhost:5173>**

Notes:
- `dev/backend/.env` must contain `LLM_API_KEY` (it does) — needed for CB4 answers
  (Q&A page and the assistant widget's generated answers).
- The **first pill analysis is slow** (model load + a fresh OCR subprocess per call —
  the frozen two-process constraint). Later calls are faster but still tens of seconds.
- Do **not** run Ollama while testing pill analysis (GPU contention). Ollama is only
  needed for the offline-fallback Q&A voice, never for the CB4 path.
- Rx scan OCR runs PaddleOCR on CPU — a full label photo can take ~2 minutes.
- Stop servers with Ctrl+C in each terminal.

## 2. Test accounts (seeded 2026-07-19, all password `PillSafe1`)

5 patient profiles covering all 15 NB07 OTC eval DINs (3 confirmed DINs each).
Re-seed anytime (idempotent) — script: `dev/backend/scripts/seed_test_profiles.py`
(`cd dev\backend && .\venv\Scripts\python.exe scripts\seed_test_profiles.py`).

| Email | Name | Lang | Confirmed medications (DIN) |
|---|---|---|---|
| `margaret@test.com` | Margaret Miller | EN | GRAVOL (00013803) · TYLENOL EXTRA STRENGTH (00559407) · ASPIRIN 81MG (02237726) |
| `henri@test.com` | Henri Tremblay | FR | ADVIL (01933558) · SENOKOT S (00026123) · PEPCID AC (02273357) |
| `fatima@test.com` | Fatima Khan | EN | BENADRYL ALLERGY (02017849) · MOTRIN 400MG (02242658) · DULCOLAX (00254142) |
| `wei@test.com` | Wei Chen | EN | NAPROXEN (02362430) · BENYLIN C&S DAY (02273462) · MUSCLE & BACK PAIN RELIEF (02230790) |
| `rosa@test.com` | Rosa Alvarez | EN | ALLERGY REMEDY / cetirizine (02375990) · BENYLIN C&S NIGHT (02306409) · DIARRHEA RELIEF (02256452) |

All prescriptions are ACTIVE with `din_confirmed = true`, so each account's profile-DIN
list feeds the pill-verify path immediately.

## 3. Suggested test flows

1. **Pill verify (the headline path):** log in as the owner of a pill you have on hand
   (e.g. `margaret@test.com` + a GRAVOL tablet), Dashboard → Scan Pill → pill photo on the
   capture card. Expect verify (green) for an own-profile pill; reject (red) or abstain
   (amber, with flip/shortlist action) for a pill from a *different* account's profile —
   e.g. photograph ADVIL while logged in as Margaret.
2. **Q&A + CB4:** Dashboard → Ask about my medication. Try "Can I take aspirin with food?" (confirm flow →
   cited CB4 answer), a dosing question (expect the hard refusal), and switch language
   to French. As `henri@test.com`, ask about warfarine to see the French path.
3. **Assistant widget (public pages):** ask "What is MyPillSafe?" (high-confidence CB4
   answer), then "can I take ibuprofen with warfarin?" (expect the redirect button to the
   guarded Q&A — the widget itself must refuse). Try FR, and hold-to-record voice.
4. **Register a fresh account** and scan a real Rx label (CPU OCR, ~2 min) → confirm the
   suggested DINs on the "Is this your medication?" panel — never auto-committed.
5. **Mobile/PWA:** resize to phone width (or Chrome device toolbar 360px) — bottom tab
   bar, no horizontal scroll. Chrome on desktop: the install icon in the address bar
   installs the PWA (localhost counts as a secure origin; a phone would need HTTPS).

## 4. Known behaviour (not bugs)

- Abstain is the common case for pill checks — the design accepts low commit-rate to
  minimize false accepts. Amber ≠ failure.
- DIN-scoped "side effects" questions may abstain (frozen-BB3 WP3 routing gap);
  ingredient-scoped phrasing answers richly.
- Avoid "maximum daily dose of X" phrasing (frozen-BB3 F9-17 "daily" token quirk);
  use "how much X can I take" — dosing questions are refused by design either way.
- The widget's med-intent gate is deliberately broad: even "does MyPillSafe remind me to
  take my medication?" redirects to the guarded Q&A ("take" triggers it).
