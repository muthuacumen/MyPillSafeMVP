# Post-Restart Checklist -- Armed Production Sidecar

Run this **every time the laptop reboots, sleeps, or the sidecar is restarted** before
a live mypillsafe.ca demo. Whole pass takes about 3 minutes, most of it the one cold
scan. Companion to `DEPLOY_GUIDE.md` and `DEPLOY_GUIDE_M1_TwoStageReader.md`; this file
is the short operational path, those are the reference.

Last executed: 2026-08-14 (post-reboot, all five steps PASS).

---

## Step 1 -- Scheduled tasks up, with a NEW banner

```bat
schtasks /query /tn "MyPillSafe Sidecar" /fo list /v
schtasks /query /tn "PillSafe\OllamaHealthCheck" /fo list
```

Healthy sidecar = `Status: Running` and `Last Result: 267009`. **267009 means RUNNING**
-- it is the healthy code, not an error. `0` appears only after a clean exit, and
`1073807364` (0x40010004) means the process was terminated (e.g. by the reboot).

The task is `Logon Mode: Interactive only`, so **a reboot does not necessarily restart
it.** Confirm with a banner dated after the boot, never by task state alone:

```powershell
(Get-CimInstance Win32_OperatingSystem).LastBootUpTime
Select-String -Path "D:\Projects\PillSafe\logs\sidecar.log" -Pattern "sidecar start" |
  Select-Object -Last 2 | ForEach-Object { $_.Line }
```

The newest `---- sidecar start <date> ----` must be **later than** the boot time. A
banner that predates the boot is a stale banner from the previous session -- treat it
as not started. Cross-check that nothing is listening yet with `netstat -ano | findstr :8100`.

If it did not start:

```bat
schtasks /run /tn "MyPillSafe Sidecar"
```

then re-verify the banner and status. Startup to first `/health` 200 takes ~15-30 s.

## Step 2 -- Ollama up

```powershell
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

Expect a version string (observed `0.31.2`). Ollama backs `/rx/extract`; if it is down,
`/health` reports `rx_extract` as `ollama_unreachable` and pill scanning still works.

## Step 3 -- /health, and confirm the reader is ARMED

The bind IP is the `--host` argument in `D:\Projects\PillSafe\ops\start_sidecar.cmd`
(currently `100.119.95.105`). The sidecar binds the tailnet IP **only** -- `127.0.0.1`
will not answer.

```powershell
Invoke-RestMethod http://100.119.95.105:8100/health | ConvertTo-Json -Depth 4
```

Required values:

| Field | Expected |
| --- | --- |
| `status` / `imb1_ok` / `sb2_ok` / `bb3_ok` | `ok` / all `true` |
| `reference_rows` / `profile_reference_rows` | `7055` / `11609` |
| `torch_cuda_available` | `true` (on the Windows laptop) |
| `ocr_worker` / `rx_extract` | `present` / `ok` |
| `reader.reader_enabled` | `true` |
| `reader.reader_mode` | `two_stage` |
| `reader.stage1_backend` | `single` |
| `reader.stage2_deps_ok` | `true` |
| `reader.scorer_load_error` | `null` |
| `reader.scorer_loaded` | `false` before warm-up -- **normal**, the scorer is lazy |

`scorer_loaded: false` is not a failure. It flips to `true` after the first scan.

## Step 4 -- Warm-up scan (cold), then one warm confirm

Do this **before** the demo, not during it. The first armed scan pays the 4-bit VLM load
once; every scan after is fast.

> **Token form is load-bearing.** `profile_dins` is a **JSON array string** whose
> elements are the **SB2 token form: `DIN` + the UNPADDED number** -- `["DIN13803"]`,
> **not** `["DIN00013803"]`, even though the image filename carries the zero-padded DIN.
> A padded or bare-number token silently produces `decision: reject` with `faces: []`.

```bash
curl -s -X POST "http://100.119.95.105:8100/pill/analyze" \
  -F "image=@/d/Projects/PillSafe/archive/demoprep/lean/pills/DIN00013803_DarkGrey_ColourRef_Front_DL.jpg" \
  -F 'profile_dins=["DIN13803"]' --max-time 180
```

Then one warm confirm with the naproxen image
`DIN02362430_DarkGrey_ColourRef_Front_DL.jpg` and `profile_dins=["DIN2362430"]`.

Known-good references -- compare against these, they are the regression bar:

| Scan | DIN token | decision | top1 | margin (ref) | latency |
| --- | --- | --- | --- | --- | --- |
| Cold warm-up | `DIN13803` | `verify` | `gravol` | **14.54** | 43-81 s |
| Warm confirm | `DIN2362430` | `verify` | `naproxen` | **22.01** | 9-14 s |

`faces` must be populated (one `f0` entry with a `read` block, `gated: false`).
Empty `faces` with a `verify`/`reject` decision means the token form is wrong, not that
the reader is broken.

## Step 5 -- Droplet reach check (read-only, required after EVERY sidecar restart)

The live backend on the droplet calls the sidecar at the raw tailnet IP. This is
`DEPLOY_GUIDE.md` CHECKPOINT 11 / `DEPLOY_GUIDE_M1_TwoStageReader.md` CHECKPOINT 10.
Run over SSH to the droplet:

```bash
sudo docker exec pillsafe_backend curl -s -m 5 -o /dev/null -w '%{http_code}\n' http://100.119.95.105:8100/health
```

Expect `200`. `curl` is present in the backend runtime image (`dev/backend/Dockerfile`
installs it and the image `HEALTHCHECK` uses it). If a future image drops it, the
guides' equivalent form is:

```bash
sudo docker exec pillsafe_backend python -c "import httpx; print(httpx.get('http://100.119.95.105:8100/health', timeout=5).status_code)"
```

Container name is `pillsafe_backend` (`docker/docker-compose.yml`; the prod overlay
`docker/docker-compose.prod.yml` swaps the image to GHCR but keeps the name).

The IP is recorded in exactly two places and nowhere else: the `--host` argument in
`ops\start_sidecar.cmd`, and `BRAINS_SERVICE_URLS` in `/opt/mypillsafe/repo/.env` on the
droplet. **Never a MagicDNS hostname** -- containers use Docker's resolver and will not
resolve tailnet names. If the laptop's tailnet IP ever changes, both must be updated.

## Step 6 -- Demo provisioning and dry run (not covered above)

Accounts, seeded data and the demo script are a separate gate. See
`DEPLOY_GUIDE_M1_TwoStageReader.md` **section 4 (Live-demo provisioning at
mypillsafe.ca)** and `D:\Projects\PillSafe\archive\demoprep\lean\demo_execution.md`.

Key trap: `POST /dev/seed-admin` returns **404 in production**, so the localhost recipe
in `DEMO_RUNBOOK.md` cannot be used -- every demo account must go through
register -> admin-approve by hand.

---

## Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| `decision: reject` **and** `faces: []` | DIN token mismatch -- padded/bare token instead of `DIN` + unpadded number | Fix the token form and re-scan. **Do NOT restart or disarm the sidecar** -- it is healthy |
| Blank dashboard after login | Stale JWT in the browser | Fresh browser session (or incognito) and log in again. Not a backend fault |
| `422 READER_ERROR_RETRYABLE` | Transient reader failure | Retry the scan **once**. If it repeats, roll back (R1) |
| First scan takes ~1 minute | Lazy 4-bit VLM scorer loading | Expected, **once per sidecar start**. This is exactly what step 4 pre-pays |
| `/health` refuses connection on `127.0.0.1` | Sidecar binds the tailnet IP only | Use `http://100.119.95.105:8100` |
| Task `Ready` + banner older than boot | Interactive-only task did not auto-start | `schtasks /run /tn "MyPillSafe Sidecar"` |
| CUDA OOM on first armed scan | 4-bit VLM and Ollama competing for 8.6 GB VRAM | `ollama stop qwen3-vl:latest` before the scan, or R1 |

## Rollback R1 -- disarm the reader (~40 s, no code changes)

Almost always the right answer. The reader is a config switch by design.

> **[2026-08-18] SUPERSEDED.** `PILLSAFE_READER=off` is retired and now fails config load
> -- the legacy engine was removed from IMB1 by owner order. Reader rollback is no longer
> an env-var flip: restore the archived change set per
> `archive/2bdeleted/2026-08-18_paddleocr_reland/MANIFEST.md` (canon path of the cmd
> today: `D:\Projects\PillSafe\Production\ops\start_sidecar.cmd`). Steps 1-2 below are
> kept as history; do not execute step 1.

1. Edit `D:\Projects\PillSafe\ops\start_sidecar.cmd`, set `PILLSAFE_READER=off`
   (line 10, currently `two_stage`).
2. Restart the task:

```bat
schtasks /end /tn "MyPillSafe Sidecar"
schtasks /run /tn "MyPillSafe Sidecar"
```

3. Re-verify: new banner, `/health` shows `reader.reader_enabled: false`, then re-run
   the step 5 droplet reach check.

Scanning continues without the two-stage reader. Do **not** pip-install anything with
the site live -- disarm first, diagnose after.
