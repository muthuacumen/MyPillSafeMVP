# MyPillSafe — Production Deploy Guide (Part B: infrastructure)

**Target:** `https://mypillsafe.ca` serving the app from the existing DigitalOcean
droplet, with all heavy ML (IMB1 vision, SB2 matcher, BB3 Q&A retrieval, **and OB5's
prescription OCR**) running on team laptops reached over a private Tailscale mesh.

**Audience:** a Sonnet agent driving Muthu through this step by step, one step at a
time. **Written 2026-07-27 by PillSafe SA.**

---

## How to use this guide (instructions for the assisting agent)

- Work **one step at a time**. After each ✅ CHECKPOINT, show Muthu the actual command
  output and get his go-ahead before moving on. Do not batch steps together.
- Commands are labelled **[LAPTOP]** (Windows PowerShell) or **[DROPLET]** (bash over
  SSH). Do not mix them up — they are different shells on different machines.
- Anything in `<angle brackets>` is a value Muthu must supply or that an earlier step
  produced. Never invent one. If you don't have it, ask.
- **This droplet hosts two live third-party sites** (JidokaAcumen and PathoIntern QA).
  Several steps exist purely to protect them. Never skip a step that mentions them.
- If a checkpoint fails, **stop and diagnose**. Do not proceed hoping it resolves.
  There is a triage table at the end (§11).

---

## 0. Facts and prerequisites

| Thing | Value |
|---|---|
| Droplet | `134.122.34.26`, tor1, 2 vCPU / 4 GB RAM / 4 GB swap / 80 GB disk |
| Already running on it | JidokaAcumen (bare-metal uvicorn, **as root, uncapped**) + PathoIntern QA (3 containers) + host nginx on `:80` |
| Free budget on it | ~1.5 GB RAM, ~31 GB disk |
| Domain | `mypillsafe.ca`, registered at **IONOS** |
| New git remote | `https://github.com/muthuacumen/MyPillSafeMVP.git` |
| Container registry | GHCR — `ghcr.io/muthuacumen/mypillsafe-{backend,frontend}` |
| Sidecar | Host-run on a laptop, port `8100`, reached over Tailscale |

**No droplet resize is needed.** The earlier sizing report recommended 4 GB → 16 GB,
but that assumed BB3's 6 GB memmap ran *on the droplet*. With the sidecar on a laptop,
the droplet carries only the backend, SPA, Postgres and nginx (~550 MB typical). Stay
on 4 GB and save the money.

### Blocking prerequisite

**Part A must be built and verified first.** This guide depends on files Part A
creates: `docker/docker-compose.prod.yml`, `docker/nginx/mypillsafe.ca.conf`,
`.env.production.example`, the slimmed backend image, the sidecar's
`/ocr/prescription` endpoint, and the `BRAINS_SERVICE_URLS` pool. If those don't
exist, stop — Part A isn't done.

Verify before starting:

```powershell
# [LAPTOP]
cd D:\Projects\PillSafe\PillSafe
Test-Path docker\docker-compose.prod.yml, docker\nginx\mypillsafe.ca.conf, .env.production.example
```

All three must be `True`.

### What Muthu needs to have ready

- SSH access to the droplet (he already has it).
- A GitHub Personal Access Token with **`write:packages`** scope (for pushing images).
- IONOS account login (for the DNS records).
- Docker Desktop running on the laptop.

---

## 1. Swap the git repo

The old remote (`muthuacumen/mypillsafe`) is being retired for
`muthuacumen/MyPillSafeMVP`.

### 1.1 — Secrets sweep BEFORE pushing anywhere

```powershell
# [LAPTOP]
cd D:\Projects\PillSafe\PillSafe
git ls-files | Select-String -Pattern "\.env$|\.env\.|\.db$|venv/|uploads/"
git grep -nI -e "sk-ant-" -e "BEGIN PRIVATE KEY" -e "POSTGRES_PASSWORD=" -- . ":(exclude)*.example"
```

**Expected:** the first command returns only `.env.example` (and Part A's
`.env.production.example`). The second returns nothing.
If either returns anything else, **stop** — a secret is tracked and must be removed
from history before pushing.

### 1.2 — Create the new repo

Muthu creates `MyPillSafeMVP` on GitHub — **empty**, no README, no .gitignore, no
license (any of those create a commit that conflicts with the existing history).

### 1.3 — Repoint and push

```powershell
# [LAPTOP]
git remote set-url origin https://github.com/muthuacumen/MyPillSafeMVP.git
git remote -v
git add -A
git status --short          # review before committing
git commit -m "Deploy readiness: remote OCR, sidecar pool, production compose"
git push -u origin main
```

✅ **CHECKPOINT 1:** `git remote -v` shows `MyPillSafeMVP`; the push succeeds; the
GitHub web UI shows the files.

**Only now** should Muthu delete the old `mypillsafe` repo. Deleting it before a
successful push means losing the only remote copy.

---

## 2. Join laptop and droplet to a Tailscale mesh

Tailscale is a WireGuard mesh: the droplet and the laptops get private `100.x.y.z`
addresses and can reach each other directly, **without the sidecar ever being exposed
to the public internet**. That is what makes it safe to run an unauthenticated ML
service on a laptop and call it from a public web server.

### 2.1 — Laptop

Install from `https://tailscale.com/download/windows`, sign in (GitHub/Google), then:

```powershell
# [LAPTOP]
tailscale ip -4
```

Record the result as `<LAPTOP_TS_IP>` (looks like `100.101.102.103`).

### 2.2 — Droplet

```bash
# [DROPLET]
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

It prints a URL — Muthu opens it and authorises the droplet **into the same
Tailscale account** as the laptop. Then:

```bash
# [DROPLET]
tailscale ip -4
tailscale status
```

✅ **CHECKPOINT 2:** `tailscale status` on the droplet lists both the droplet and the
laptop.

### 2.3 — Ping across the mesh

```bash
# [DROPLET]
tailscale ping <LAPTOP_TS_IP>
```

✅ **CHECKPOINT 3:** the ping succeeds (it may say "via DERP" first, then direct —
either is fine).

---

## 3. Make the sidecar reachable over the tailnet

Two things currently prevent this, and both are deliberate local-dev defaults:

1. The sidecar binds `127.0.0.1`, which accepts nothing from outside the machine.
2. Windows Firewall blocks inbound `:8100`.

### 3.1 — Bind the sidecar to its tailnet address

Bind to the **tailnet IP specifically**, not `0.0.0.0` — that way the sidecar is
reachable over Tailscale but still invisible on café Wi-Fi or the home LAN.

```powershell
# [LAPTOP]  (from D:\Projects\PillSafe\PillSafe\dev\brains)
.\.venv\Scripts\python.exe -m uvicorn app:app --host <LAPTOP_TS_IP> --port 8100
```

Leave this running in its own terminal.

### 3.2 — Allow inbound 8100 on the Tailscale interface only

Run PowerShell **as Administrator**:

```powershell
# [LAPTOP - ADMIN]
New-NetFirewallRule -DisplayName "MyPillSafe sidecar (Tailscale)" `
  -Direction Inbound -Protocol TCP -LocalPort 8100 `
  -RemoteAddress 100.64.0.0/10 -Action Allow
```

`100.64.0.0/10` is the Tailscale address range — this rule admits tailnet traffic and
nothing else.

### 3.3 — Verify from the droplet

```bash
# [DROPLET]
curl -s http://<LAPTOP_TS_IP>:8100/health | head -40
```

✅ **CHECKPOINT 4:** JSON comes back with the brains loaded, `reference_rows: 7055`,
and `ocr_worker: "present"`. If it hangs → firewall (3.2). If "connection refused" →
the sidecar is bound to the wrong address (3.1).

### 3.4 — Keep the laptop awake

The site's pill-scan, Rx-scan and Q&A features are live only while a sidecar is. Before
any demo:

```powershell
# [LAPTOP - ADMIN]
powercfg /change standby-timeout-ac 0
powercfg /change standby-timeout-dc 0
```

Restore afterwards with `powercfg /change standby-timeout-dc 10` (**not** 600 — large
values take minutes to apply).

### 3.5 — Additional team sidecars (optional, do later)

Each extra member needs, on their own machine: Tailscale (joined to the same account
as a device), the sidecar venv (~3–4 GB), and the three frozen packages —
`IMB1_v0` (0.19 GB), `SB2` (small), **`BB3` (8.07 GB)**. That is ~12 GB per laptop, so
realistically Muthu's is the only complete sidecar at first. The pool built in Part A
makes more *possible*; it does not create them. Add each member's
`http://<their_ts_ip>:8100` to `BRAINS_SERVICE_URLS` as they come online.

---

## 4. Build and push images from the laptop

Building on the droplet would spike `npm run build` (1–2 GB) on a box with 1.5 GB free
next to a live site. Build here, ship the result.

```powershell
# [LAPTOP]
cd D:\Projects\PillSafe\PillSafe
$env:CR_PAT = "<github_pat_with_write_packages>"
$env:CR_PAT | docker login ghcr.io -u muthuacumen --password-stdin

$TAG = Get-Date -Format "yyyyMMdd-HHmm"
docker build -t ghcr.io/muthuacumen/mypillsafe-backend:$TAG  -t ghcr.io/muthuacumen/mypillsafe-backend:latest  dev\backend
docker build -t ghcr.io/muthuacumen/mypillsafe-frontend:$TAG -t ghcr.io/muthuacumen/mypillsafe-frontend:latest dev\frontend

docker push ghcr.io/muthuacumen/mypillsafe-backend:$TAG
docker push ghcr.io/muthuacumen/mypillsafe-backend:latest
docker push ghcr.io/muthuacumen/mypillsafe-frontend:$TAG
docker push ghcr.io/muthuacumen/mypillsafe-frontend:latest

Write-Host "Deployed tag: $TAG"
```

**Record `$TAG`** — it is the rollback handle.

Then on GitHub: *Profile → Packages → each package → Package settings → Change
visibility → **Public***. This lets the droplet pull without storing a token. (If
Muthu prefers them private, he must instead `docker login ghcr.io` on the droplet with
a `read:packages` token.)

✅ **CHECKPOINT 5:** both packages appear under the GitHub profile with the new tag.

---

## 5. Droplet pre-flight (protect the neighbours)

```bash
# [DROPLET]
free -h
df -h /
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
sudo ss -tlnp | grep -E ':(80|8080|8000|5433|6379)\s'
sudo nginx -T 2>/dev/null | grep -E "server_name|listen " | head -30
```

Record for comparison later: current free RAM, and that JAcI + PathoIntern are up.

**Two things must be true before continuing:**
1. **Port 8080 is free** (nothing in the `ss` output binds it). If something does, pick
   another loopback port and change it in both `docker-compose.prod.yml` and
   `mypillsafe.ca.conf`.
2. **Host nginx owns `:80`** — that is why the PillSafe stack must never publish `:80`.

### 5.1 — Apply pending updates and reboot (do this now, not near demo day)

The earlier droplet report flagged `*** System restart required ***` and 27 pending
updates (1 security). Warn Muthu this briefly takes both live sites down, and get
explicit confirmation of the timing first.

```bash
# [DROPLET]
sudo apt update && sudo apt upgrade -y
sudo reboot
```

Wait ~60s, reconnect, and confirm JAcI and PathoIntern came back:

```bash
# [DROPLET]
docker ps
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80
```

✅ **CHECKPOINT 6:** both neighbour sites respond exactly as they did before the reboot.

> **Expect `301`, not `200`, from `http://127.0.0.1:80` once §9 has run certbot.**
> That is the HTTP→HTTPS redirect on the default vhost — the correct post-TLS
> answer, not a neighbour regression. Only a connection failure or a 5xx is a
> problem here. Note also that JidokaAcumen is bare-metal uvicorn and so never
> appears in `docker ps` — verify it over HTTP, not from the container list.

### 5.2 — Swap headroom (cheap OOM insurance)

```bash
# [DROPLET]
free -h | grep -i swap
```

If swap is under 8 GB and disk allows, enlarge it. Swap is a safety net — never a
place to actually run a workload.

---

## 6. DNS at IONOS

In the IONOS control panel, under the domain's DNS settings for `mypillsafe.ca`:

| Type | Host / Name | Value | TTL |
|---|---|---|---|
| A | `@` | `134.122.34.26` | 3600 (lower during setup if offered) |
| A | `www` | `134.122.34.26` | 3600 |

Remove or repoint any parking/forwarding record IONOS created by default — a leftover
redirect will silently hijack the domain and make TLS issuance fail confusingly.

Then wait for propagation:

```bash
# [DROPLET]
dig +short mypillsafe.ca
dig +short www.mypillsafe.ca
```

✅ **CHECKPOINT 7:** both return `134.122.34.26`. **Do not proceed to TLS (§9) until
this is true** — Let's Encrypt validates over the public DNS record, so certbot will
fail while propagation is incomplete. Propagation is usually minutes, occasionally
hours.

---

## 7. Put the app on the droplet

### 7.1 — Directory and files

```bash
# [DROPLET]
sudo mkdir -p /opt/mypillsafe
cd /opt/mypillsafe
sudo git clone https://github.com/muthuacumen/MyPillSafeMVP.git repo
```

(A full clone is the simplest way to get the compose and nginx files, and makes future
updates a `git pull`. The images come from GHCR — nothing is built here.)

### 7.2 — Production environment file

```bash
# [DROPLET]
cd /opt/mypillsafe/repo
sudo cp .env.production.example .env
sudo nano .env
```

Fill in, at minimum:

| Variable | Value |
|---|---|
| `APP_ENV` | `production` |
| `SECRET_KEY` | a fresh random 64-char string (`openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | a fresh strong password |
| `FRONTEND_ORIGIN` | `https://mypillsafe.ca` |
| `OPENAPI_ENABLED` | `false` |
| `OCR_PIPELINE_ENABLED` | `true` — **never `false` in production**, it fabricates prescription text |
| `BRAINS_SERVICE_URLS` | `http://<LAPTOP_TS_IP>:8100` (comma-separate more as members join) |
| `LLM_API_KEY` | Muthu's Anthropic key (CB4's voice) |
| `IMAGE_TAG` | the `$TAG` from §4 |

```bash
# [DROPLET]
sudo chmod 600 .env
```

> **Use the raw Tailscale IP `100.x.y.z`, never a MagicDNS hostname.** Containers use
> Docker's resolver and will not resolve tailnet names — the hostname form fails in a
> way that looks like the sidecar is down.

> **Cost note:** with open registration and a real `LLM_API_KEY`, anyone who registers
> can spend Anthropic tokens. Set a spend limit in the Anthropic console — the app's
> rate limiter is not a billing control.

### 7.3 — Render the config and prove nothing binds publicly

```bash
# [DROPLET]
cd /opt/mypillsafe/repo
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env config | grep -A3 "ports:"
```

✅ **CHECKPOINT 8 — the one that protects the live sites:** every published port must
be `127.0.0.1:...`. There must be **no `0.0.0.0`** and **no host `:80`** anywhere in
that output. If there is, stop — bringing the stack up would take JidokaAcumen down.

### 7.4 — Start it

```bash
# [DROPLET]
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml ps
curl -s -o /dev/null -w "gateway:%{http_code}\n" http://127.0.0.1:8080
curl -s http://127.0.0.1:8080/health
```

✅ **CHECKPOINT 9:** all five containers up — postgres, redis, backend and
frontend report `(healthy)`; the gateway nginx has **no healthcheck** and shows
plain `Up`, which is correct, not a failure. Gateway returns 200; `/health`
returns `{"status":"ok"}`.

### 7.5 — Confirm the neighbours survived

```bash
# [DROPLET]
docker ps --format "table {{.Names}}\t{{.Status}}"
free -h
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:80
```

✅ **CHECKPOINT 10:** JAcI and PathoIntern still healthy; free RAM still positive with
room to spare. As at CHECKPOINT 6, `http://127.0.0.1:80` returns **`301`** once TLS
is in place (the certbot redirect), and JidokaAcumen is verified over HTTP rather
than in `docker ps`.

### 7.6 — Verify the container can actually reach the sidecar

This is the step that catches the tailnet-routing gotcha:

```bash
# [DROPLET]
sudo docker exec pillsafe_backend python -c "import httpx; print(httpx.get('http://<LAPTOP_TS_IP>:8100/health', timeout=5).status_code)"
```

✅ **CHECKPOINT 11:** prints `200`. If it fails while §3.3's `curl` from the droplet
host worked, the problem is container→tailnet routing, not Tailscale itself — see §11.

### 7.7 — Verify DB schema parity (MANDATORY on any redeploy)

**This step exists because skipping it took the site down on 2026-07-30.** The
app is code-first: `create_all` creates missing *tables* but **never alters an
existing one**, so a column added to a model since the last deploy does not
reach Postgres by itself. The symptom is brutal and misleading — the brains all
answer `200`, and then every read AND write of that table returns 500. On
2026-07-30 that meant `GET /prescriptions/me` 500 (My Medications *and* the 30 s
dose-reminder poll dead) plus every Rx scan failing after three healthy sidecar
calls, which looks exactly like a broken scanner rather than a missing column.

```bash
# [DROPLET] every column the models declare must exist in Postgres
sudo docker exec -i pillsafe_backend python - <<'PY'
import asyncio
from sqlalchemy import inspect
from app.core.database import engine, Base
import app.models.user, app.models.patient, app.models.analysis, app.models.prescription  # noqa

async def main():
    async with engine.begin() as conn:
        live_tables = await conn.run_sync(lambda c: set(inspect(c).get_table_names()))
        bad = 0
        for table in Base.metadata.sorted_tables:
            if table.name not in live_tables:
                print(f"{'TABLE MISSING':<42} {table.name}"); bad += 1; continue
            cols = await conn.run_sync(
                lambda c, n=table.name: {col["name"] for col in inspect(c).get_columns(n)})
            missing = {c.name for c in table.columns} - cols
            print(f"{('MISSING ' + str(sorted(missing))) if missing else 'ok':<42} {table.name}")
            bad += bool(missing)
        print("SCHEMA PARITY: FAIL" if bad else "SCHEMA PARITY: OK")

asyncio.run(main())
PY
```

✅ **CHECKPOINT 11b:** every table prints `ok`. If anything prints `MISSING`, the
boot-time sync did not cover it — apply the repair script and re-check:

```bash
# [DROPLET] idempotent, additive-only, safe to re-run
sudo docker exec -i pillsafe_postgres psql -U pillsafe_user -d pillsafe \
  < /opt/mypillsafe/repo/docker/fix_prescriptions_schema.sql
```

The permanent guard is the dialect-aware sync in `app/core/database.py`
(`_add_missing_columns`, now running on Postgres as well as SQLite) plus
`dev/backend/tests/test_column_sync.py`, whose parity test fails if a model
column is ever added without registering it there.

---

## 8. Host nginx site

```bash
# [DROPLET]
sudo cp /opt/mypillsafe/repo/docker/nginx/mypillsafe.ca.conf /etc/nginx/sites-available/mypillsafe.ca
sudo ln -s /etc/nginx/sites-available/mypillsafe.ca /etc/nginx/sites-enabled/mypillsafe.ca
sudo nginx -t
```

(If this droplet doesn't use the `sites-available`/`sites-enabled` layout, put the file
in `/etc/nginx/conf.d/mypillsafe.ca.conf` instead — check what the existing JAcI and
PathoIntern sites do and match it.)

✅ **CHECKPOINT 12:** `nginx -t` says *syntax is ok / test is successful*. **Never
reload with a failing config** — it would take the live sites down with it.

```bash
# [DROPLET]
sudo systemctl reload nginx
curl -s -o /dev/null -w "%{http_code}\n" -H "Host: mypillsafe.ca" http://127.0.0.1
```

✅ **CHECKPOINT 13:** returns 200, and JAcI + PathoIntern still respond on their own
hostnames.

---

## 9. TLS

Requires CHECKPOINT 7 (DNS resolving publicly).

```bash
# [DROPLET]
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d mypillsafe.ca -d www.mypillsafe.ca
```

Choose **redirect HTTP → HTTPS** when prompted. Certbot rewrites the site file in
place. Then:

```bash
# [DROPLET]
sudo nginx -t && sudo systemctl reload nginx
sudo certbot renew --dry-run
systemctl list-timers | grep -i certbot
```

✅ **CHECKPOINT 14:** `https://mypillsafe.ca` loads the MyPillSafe landing page in a
browser with a valid padlock; the renewal dry-run succeeds; a renewal timer is active.

HTTPS is also a hard requirement for the PWA — service workers only register on a
secure origin, so installability starts working at this point, not before.

---

## 10. End-to-end verification

Run these in a browser against `https://mypillsafe.ca`, with the sidecar up. Test
credentials and seeded profiles are in `documentation/integration/LOCAL_TESTING.md`
(the seeded accounts are local — register a fresh account here).

| # | Check | Expected |
|---|---|---|
| 1 | Landing + all 5 about pages | Render, navy brand, no fabricated stats |
| 2 | Register → login | Works; a wrong password shows an inline error (no reload) |
| 3 | Rx scan with a real label photo | **Real OCR text reaches the parser** — see the two failure signatures below before judging this one |
| 4 | DIN suggestions → confirm | Suggestion list appears; confirming persists |
| 5 | Pill scan, correct pill | `verify` — green |
| 6 | Pill scan, wrong pill | `reject` — red |
| 7 | Pill scan, ambiguous/flip | `abstain` — **amber, never styled as red or green** |
| 8 | Q&A: *"Can I take celecoxib if I'm allergic to sulfa drugs?"* | Answer begins **"No"** and cites **a celecoxib DIN whose contraindications carry the sulfonamide bar**. This is the F9-11 polarity probe — a "Yes" here is a serious regression. **Do NOT require DIN 2239942**: post-WP-F5 the packer selects generic celecoxib monographs by score, so pinning one DIN files a false regression. The load-bearing criteria are the "No" and the sulfonamide citation, not which DIN supplies it |
| 9 | Q&A in French | Localized answer, citations intact |
| 10 | PWA install | Install prompt available; app opens standalone |
| 11 | Mobile 360px | No horizontal scroll; 5-tab bottom bar fits |
| 12 | Disclaimers | Present on every result surface |

> **Reading check 3 — two different-looking failures, only one is a deploy
> problem.**
> (a) The **verbatim demo string** — *"Metformin HCl 500mg — twice daily with
> meals. Dr. A. Chen."* — for an unrelated label means OCR fell back to
> fabricated text (`OCR_PIPELINE_ENABLED` is false). **Stop and fix**; this
> must never happen in production.
> (b) A real-looking but **wrong** drug name — e.g. the pharmacy's own name
> ("… PHARMACY") extracted as the medication — is the **known pre-existing
> `prescription_parser.py` real-label heuristics bug** (ADR 2026-07-27,
> unassigned): OCR worked, the parser picked the wrong line. Note it, have
> Muthu correct the field in the UI, and continue — do **not** stall the
> deploy diagnosing it.

### 10.1 — Degradation check (do not skip)

Stop the sidecar on the laptop (Ctrl-C), then:

| Check | Expected |
|---|---|
| Landing / about / login / register | **Still work** — the public site must not depend on any sidecar |
| Rx scan | Clear "temporarily unavailable" error — **never fabricated text** |
| Pill scan | Clear service-unavailable message |
| Med Q&A | Clear service-unavailable message |

✅ **CHECKPOINT 15:** all of the above. Restart the sidecar and confirm everything
recovers without restarting the droplet stack.

### 10.2 — Resource check

```bash
# [DROPLET]
docker stats --no-stream
free -h
```

✅ **CHECKPOINT 16:** PillSafe containers are well under their `mem_limit` caps and the
box still has comfortable free RAM.

---

## 11. Triage

| Symptom | Likely cause | Fix |
|---|---|---|
| JAcI or PathoIntern went down | The stack published `:80` | `docker compose ... down` immediately, then re-check CHECKPOINT 8 |
| `certbot` fails | DNS not propagated, or an IONOS parking/redirect record still active | Re-run CHECKPOINT 7; clear the parking record |
| Pill/Rx/Q&A all 503 | Sidecar down, laptop asleep, or wrong IP in `BRAINS_SERVICE_URLS` | §3.3 then CHECKPOINT 11 |
| Droplet host `curl` reaches the sidecar but the container can't | Container→tailnet routing | Confirm the **raw 100.x IP** (not MagicDNS) is in `.env`; check `sysctl net.ipv4.ip_forward` = 1; as a last resort advertise the route or run the backend with `network_mode: host` |
| Rx upload returns 413 | `client_max_body_size` too small | Must be ≥ 20M in **both** the host site file and the container gateway |
| Rx upload times out | `proxy_read_timeout` shorter than OCR | Raise to 300s in the host site file; compare against Part A's measured OCR time |
| Rx scan returns Metformin demo text | `OCR_PIPELINE_ENABLED=false` | Set `true`, recreate the backend container |
| Site loads but API 502 | Backend container down or gateway port mismatch | `docker compose ps`, `docker compose logs backend` |
| Anthropic 401 | Key pasted with angle brackets or quotes | Strip them (this exact bug bit once before) |

---

## 12. Operations runbook

**Ship an update**

```powershell
# [LAPTOP] — build + push (§4), note the new $TAG
```
```bash
# [DROPLET]
cd /opt/mypillsafe/repo && sudo git pull
sudo sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=<new_tag>/" .env
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d
```

**If the change touched the brains packages** (`BB3/`, `IMB1_v0/`, `SB2/`) **or `dev/brains/`,
restart the sidecar — that is the ONLY way those changes reach production.** They live on the
laptop, in no image and no compose file, so the build-and-push above ships nothing from them:
the droplet would keep calling a sidecar still running the old code. `BB3/` in particular is
laptop-local and **not in git at all** (settled 2026-07-30), so the repo is no record of its state.

```powershell
# [LAPTOP] The sidecar runs under the Task Scheduler task "MyPillSafe Sidecar"
# (D:\Projects\PillSafe\ops\start_sidecar.cmd), so it is NOT a terminal you can
# Ctrl-C. Restart it through the task, ALWAYS /end before /run:
schtasks /end /tn "MyPillSafe Sidecar"
schtasks /run /tn "MyPillSafe Sidecar"

# VERIFY IT ACTUALLY RESTARTED -- do not skip this.
# `schtasks /run` SILENTLY NO-OPS if the old instance still holds port 8100:
# it reports Last Result: 1 and starts nothing, so a brain change you believe
# you deployed is still not live. Proof of a real restart is a NEW banner:
Get-Content D:\Projects\PillSafe\logs\sidecar.log -Tail 5   # expect a fresh "---- sidecar start ... ----"
schtasks /query /tn "MyPillSafe Sidecar" /v /fo LIST | Select-String "Last Result"  # expect 0, not 1
```

Then re-confirm CHECKPOINT 11 from the droplet before calling the deploy done.

**Roll back** — set `IMAGE_TAG` to the previous tag and re-run the last command.

**Switch to a different member's sidecar** — either add their URL to
`BRAINS_SERVICE_URLS` and let health-checked failover pick it up, or pin it explicitly
via the admin endpoint `POST /api/v1/admin/brains/pin` (`GET /api/v1/admin/brains`
shows pool health).

**Logs**

```bash
# [DROPLET]
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs -f --tail=100 backend
```

**Before a live demo**
1. Start the sidecar; confirm CHECKPOINT 11 from the droplet.
2. Disable laptop sleep (§3.4).
3. **Warm the models** — one throwaway Rx scan, one pill scan, one Q&A. First calls pay
   model-load and page-cache costs; nobody wants to watch that on stage.
4. Confirm the neighbours are healthy so nothing surprises you mid-demo.

**Cost control** — check the Anthropic spend cap before any public sharing of the URL.

---

## 13. Deliberately out of scope

- Backups of the Postgres volume (add `pg_dump` on a cron before real user data exists).
- The `fail2ban` / key-only-SSH hygiene and JAcI-running-as-root smell flagged in the
  droplet report — real, but not deploy blockers.
- CI/CD (GitHub Actions → GHCR). The manual build in §4 is deliberate for a capstone.
- Any change to the frozen packages (`IMB1_v0`, `SB2`, `BB3`) — they stay frozen.
