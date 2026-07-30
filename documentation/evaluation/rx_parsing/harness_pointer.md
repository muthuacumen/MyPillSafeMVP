# How to re-run these measurements

The harness is **`documentation/deployment/redteam_llm_extraction.py`**. It is the source of truth
for the labels, the expected answers, and the scoring; the JSON files in this folder are its
output. If a number in `README.md` disagrees with a fresh run, the fresh run wins — and the
disagreement itself is a finding worth writing down (see README §6).

## Prerequisites

| run | needs |
|---|---|
| `regex` arm | nothing beyond the backend venv |
| `qwen2.5:7b` arm | Ollama on `127.0.0.1:11434` with `qwen2.5:7b-instruct` pulled |
| `haiku-4.5` arm | `LLM_API_KEY` in the repo-root `.env` or `dev/backend/.env` (billable) |
| `--via-service` | Ollama **and** the brains sidecar running at `BRAINS_SERVICE_URL` (default `127.0.0.1:8100`) |

Start the sidecar with its own venv (never the backend's — it needs torch/paddle):

```
cd dev/brains
./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100
```

`GET /health` should report `"rx_extract": "ok"`. Anything else (`ollama_unreachable`,
`model_not_pulled`) means the qwen proposer will not run and the app will fall back to the regex
proposer — which is correct behaviour, but not what you are trying to measure.

## The runs

All commands are from the repository root, using the **backend** venv.

**Three-system comparison** (writes
`documentation/deployment/redteam_llm_extraction_perfield_results.json`, copied here as
`results_three_way.json` — the pre-widening run it superseded is kept alongside it as
`results_three_way_2026-07-28_prewidening.json`):

```
dev\backend\venv\Scripts\python.exe documentation\deployment\redteam_llm_extraction.py --repeats 3
```

Add `--skip-haiku` to avoid the billable arm, `--skip-qwen` to skip the local model.

**`--repeats N` is not optional for the model arms.** qwen2.5:7b at temperature 0 is measured
non-deterministic, so a single run cannot honestly report that an intermittent error is absent —
it can only report that it did not happen that time. With `N>1` the harness prints per-run numbers,
takes the **worst** run as the headline (for an intermittent safety error, "it usually does not
happen" is not a claim a medication app gets to make), and lists which labels changed answer
between runs. The regex arm is deterministic and its stability line is the control.

**Shipped-pipeline acceptance** — the same 24 labels through the real sidecar endpoint, the real
guardrails, and the real server-side time derivation. Writes a **separate** file
(`redteam_llm_extraction_perfield_via_service_results.json`, copied here as
`results_via_service.json`, with its superseded run kept as
`results_via_service_2026-07-28_prewidening.json`) so an acceptance run can never overwrite the
published three-way record:

```
dev\backend\venv\Scripts\python.exe documentation\deployment\redteam_llm_extraction.py --via-service --repeats 3
```

This mode calls `app.api.v1.routes.prescriptions._propose_medications` — the route's own helper —
rather than re-implementing the sequence, because a harness that re-implements the thing it
measures measures the re-implementation. Two deliberate differences from the raw-model arms:

- the scored `specific_times` are the **derived reminder times** (which is what
  `HELDOUT_CASES[*]["times"]` has always encoded — e.g. H10 `BEDTIME` → `["21:00"]`); the model's
  own field is now `explicit_times` and holds only clock times literally printed on the label;
- guardrail **G1** (reference catalog cross-check) is not run — it only ever adds the informational
  `not_in_reference` flag, affects no scored field, and would make the latency incomparable with
  the single-call model arms.

Beyond the score table it prints two extra checks: which proposer actually answered
(`parse_sources_seen` — `['regex']` means the sidecar was down and you measured the fallback), and
the count of WEEKLY/PRN medications carrying a reminder time, which must be **0**.

**Re-export the label set** into this folder:

```
dev\backend\venv\Scripts\python.exe documentation\deployment\redteam_llm_extraction.py ^
  --export-labels documentation\evaluation\rx_parsing\labels_and_ground_truth.json
```

## Reading the score table

- **original 12** — the rule-based parser's own development fixtures. Scored two ways. `orig ok` is
  the historical medication-count + name-fragment metric, kept unchanged so the widened runs stay
  comparable to the pre-widening published record; 12/12 there means "did not regress", nothing
  more. `orig full` / `orig fields` / `orig ev` are the **per-field** scoring added 2026-07-29 (80
  fields), using the same function as the held-out set.
- **held-out 12** — never used to tune anything. Scored per field (name, dosage, frequency
  category, reminder times); `times: null` in the ground truth means times are not scored for that
  medication.
- **ALL fields / ALL ev** — both sets combined, 130 fields. This is the number to quote; the
  split columns exist so the home-turf and never-seen halves stay distinguishable.
- **fully-ok** — every scored field correct, the right number of medications, and zero safety
  events. It is deliberately unforgiving: one wrong field fails the whole label.
- **safety events** — phantom medication, missed medication, times on an as-needed medication,
  daily times on a **weekly** medication, or a dosage/name not present on the label. The
  `ocr_noise` cases are exempt from the last two, because repairing OCR damage is the point there.

## A standing caution

Do not run this while a GPU batch job is in progress on the same machine. Ollama and the batch will
contend for VRAM and you will measure the contention. Ollama is loaded with `keep_alive: "10m"`,
so it releases VRAM on its own about ten minutes after the last call.
