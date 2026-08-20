# MyPillSafe — Admin Panel Runbook (admin access, Sidecar Supervisor, deploys, sessions)

**Target:** the Admin Panel on `https://mypillsafe.ca` — becoming a production admin,
controlling the Sidecar Supervisor from production, shipping this feature, and the
localhost admin / session-management tooling that ships with it.

**Audience:** Muthu, self-service — the steps he runs himself. Companion to
`DEPLOY_GUIDE.md` (full infrastructure build) and `ops/supervisor/README.md` (full
Supervisor HTTP contract) — this runbook links to both rather than repeating their
content, and only quotes the exact commands its own steps need.

**Written 2026-08-19 by PillSafeOrc.**

---

> **Corrections vs. common assumptions** (verified against the actual code/docs, not
> assumed — this project has a standing rule that documented facts must be checked):
> - The droplet's production secrets file is named **`.env`** at the repo root, **not**
>   `.env.production`. `docker-compose.prod.yml` hardcodes `env_file: ../.env` in the
>   base compose file, so any other name fails with "env file not found." The repo
>   ships a template, `.env.production.example`, copied to `.env` once on first setup.
> - There is **no GitHub Actions CI/CD** in this project. Every deploy is a manual
>   `docker build` + `docker push` from the laptop, by design — see §3.
> - `ADMIN_EMAILS` **promotes an existing account, it never creates one** — register
>   first, then promote. See §1.
> - The promotion force-sets `role` and `is_active` but does not appear to touch
>   `is_verified`. This is inert under current code — neither login (`auth_service.py`)
>   nor admin gating (`app/api/deps.py`) checks `is_verified` at all, it's a display-only
>   badge — so it is **not** a cause of login or Admin-link failures. §1.4 still sets it
>   for defensive completeness. See §1.3–§1.4.

## How to use this runbook

- Commands are labelled **[LAPTOP]** (Windows PowerShell) or **[DROPLET]** (bash over
  SSH to the droplet) — do not mix them up, they are different shells on different
  machines.
- ✅ **CHECKPOINT** callouts follow risky steps — check the actual output before moving on.
- For anything this runbook only summarizes (the full deploy walkthrough, the full
  Supervisor HTTP contract), follow the link rather than re-deriving it here.

---

## 1. Become admin in production (mypillsafe.ca)

Same mechanism documented in `DEPLOY_GUIDE.md` §7.2a — repeated here because it's the
step Muthu runs himself, and will run again for any teammate later.

### 1.1 — Register a normal account

Go to `https://mypillsafe.ca/register` and sign up with
`muthuraj.jayakumar@gmail.com` like any other user. You'll land on the "awaiting
approval" screen — expected, not an error. `ADMIN_EMAILS` (next step) promotes an
*existing* account; it never creates one. Verbatim from `DEPLOY_GUIDE.md` §7.2a:

> "`/dev/seed-admin` returns **404** whenever `APP_ENV != development`, so there is no
> endpoint that mints an admin in production. `ADMIN_EMAILS` is the mechanism instead:
> on every start, the backend promotes each listed address that **already has an
> account** to `role=ADMIN, is_active=true`. It promotes, it never creates — so
> register first."

### 1.2 — Add yourself to ADMIN_EMAILS and restart the backend

```bash
# [DROPLET]
cd /opt/mypillsafe/repo
sudo nano .env
```

Set (or add to) `ADMIN_EMAILS=muthuraj.jayakumar@gmail.com` (comma-separate more
addresses for teammates). This is the real production secrets file, **`.env`** — see
the correction box above, not `.env.production`.

Restart just the backend — the exact command from `DEPLOY_GUIDE.md` §7.2a:

```bash
# [DROPLET]
cd /opt/mypillsafe/repo
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d --force-recreate backend
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml logs backend | grep ADMIN_EMAILS
```

✅ **CHECKPOINT:** the log shows `ADMIN_EMAILS: promoted <you> to active ADMIN` and a
summary line `N configured, N matched, 1 promoted`. On any later restart the same log
reads `is already an active admin` and `0 promoted` — that's the idempotent no-op, not
a failure. If it instead says `no account yet for <you>`, you skipped §1.1 — register,
then restart again.

### 1.3 — Verify

Log in at `https://mypillsafe.ca` with the registered email/password. An **Admin**
link/section should appear in the app UI. Confirm directly against the API:

```
GET https://mypillsafe.ca/api/v1/admin/stats
Authorization: Bearer <your access token>
```

Expect `200` with body shape
`{"total_users": N, "active_users": N, "total_analyses": N, "admin_count": N}`
(this exact shape was verified working locally, end to end, this session).

🔴 **If login or the Admin link doesn't work after the restart**, `is_verified` is
**not** the cause — `login_user()` in `app/services/auth_service.py` gates only on
`is_active`, and `get_current_admin()` in `app/api/deps.py` gates only on `role`;
neither reads `is_verified` anywhere. `app/services/admin_bootstrap.py` force-sets
`role=ADMIN` and `is_active=true` but does not touch `is_verified`, and that's fine —
it's a display-only "verified" badge in the admin users table, inert for login/admin
access. §1.4's direct-SQL path still sets all three columns, defensively, in case a
future check ever starts reading it.

### 1.4 — Alternative: direct SQL

If §1.2's restart-and-log flow doesn't pick up your account, or you'd rather skip the
restart wait, set all three columns directly against Postgres. Names, from
`docker-compose.yml` + `docker-compose.prod.yml`: backend container `pillsafe_backend`;
Postgres container `pillsafe_postgres` (`postgres:15-alpine`, containerized, not
managed); DB `pillsafe`, DB user `pillsafe_user`. Note the pattern is
`docker exec <container>`, not `docker compose exec <service>`:

```bash
# [DROPLET]
sudo docker exec -it pillsafe_postgres psql -U pillsafe_user -d pillsafe -c "UPDATE users SET role='ADMIN', is_active=true, is_verified=true WHERE email='muthuraj.jayakumar@gmail.com';"
```

✅ **CHECKPOINT:** repeat §1.3's login + `GET /api/v1/admin/stats` check.

---

## 2. Enable the Sidecar Supervisor for production control

The Supervisor is a small ops API (`Production/ops/supervisor/`) that lets the app's
Admin Panel start/stop the local ML sidecar on demand, instead of relying only on the
at-logon Task Scheduler job. Full HTTP contract (every endpoint, request/response
shapes, guard semantics) is in `ops/supervisor/README.md` — this section covers only
what's needed to turn it on for production use.

### 2.1 — Laptop: install and configure

```
REM [LAPTOP] from D:\Projects\PillSafe\Production\ops\supervisor
setup_supervisor.cmd      REM creates its own .venv here (separate from dev/brains/.venv), pip-installs fastapi/uvicorn/psutil/httpx/python-dotenv
copy .env.example .env
```

Edit `.env`:

| Key | Default | Set it to |
|---|---|---|
| `SUPERVISOR_TOKEN` | *(none — required, supervisor refuses to start if unset)* | a fresh random value — generate one below |
| `SUPERVISOR_HOST` | `127.0.0.1` | `100.119.95.105` (this machine's Tailscale interface) — the default binds loopback-only, which the droplet cannot reach |
| `SUPERVISOR_MIN_FREE_GB` | `3.0` | leave at default |
| `SUPERVISOR_START_TIMEOUT_S` | `300` | leave at default — seconds before an unbound `/start` is declared stalled (`state: "start_stalled"`), after which `/stop` can kill it |
| `SUPERVISOR_HEALTH_TIMEOUT_S` | `8.0` | leave at default — health-proxy budget, sized for the sidecar's own slow `/health` (~4.14s to fail) when Ollama is down |

(Port is not an `.env` key — it's hardcoded `SUPERVISOR_PORT = 8090` in `supervisor.py`.)

Generate `SUPERVISOR_TOKEN`:

```powershell
# [LAPTOP]
-join ((48..57)+(65..90)+(97..122) | Get-Random -Count 40 | % {[char]$_})
```

Start it:

```
REM [LAPTOP]
run_supervisor.cmd
```

(checks `.venv` exists, then runs `.venv\Scripts\python.exe supervisor.py`.)

### 2.2 — Task Scheduler and Firewall (manual — the Supervisor build does not do these)

`ops/supervisor/README.md`'s own "what the owner still has to do" list is explicit
that neither of these is done by the build:

> "1. **Task Scheduler**: create an at-logon task that runs `run_supervisor.cmd`
> (this is a manual step -- this build does not register or modify any Task Scheduler
> task). 2. **Tailscale**: once that task exists, set `SUPERVISOR_HOST` in `.env` to
> this machine's Tailscale interface IP ... so the production droplet's admin panel
> can reach `:8090` over the tailnet."

This runbook is the first place either is actually written down. Register the task:

```powershell
# [LAPTOP]
schtasks /create /tn "PillSafe\SidecarSupervisor" /tr "D:\Projects\PillSafe\Production\ops\supervisor\run_supervisor.cmd" /sc onlogon /rl highest /f
```

Restrict inbound `:8090` to the tailnet only — same `100.64.0.0/10` Tailscale CGNAT
range `DEPLOY_GUIDE.md` §3.2 already uses for the sidecar's own port 8100 — run as
Administrator:

```powershell
# [LAPTOP - ADMIN]
New-NetFirewallRule -DisplayName "PillSafe Supervisor (Tailscale only)" -Direction Inbound -Protocol TCP -LocalPort 8090 -RemoteAddress 100.64.0.0/10 -Action Allow
```

(a `netsh advfirewall firewall add rule ...` equivalent exists too, if PowerShell
isn't preferred — the `New-NetFirewallRule` form above is the primary path.)

✅ **CHECKPOINT:** from the droplet (or any other tailnet machine),
`curl -s -H "Authorization: Bearer <token>" http://100.119.95.105:8090/status` returns
`200` with `sidecar_running`/`free_ram_gb`/`profile` in the body.

### 2.3 — Droplet: point the backend at the Supervisor

Add to `/opt/mypillsafe/repo/.env` (the real production secrets file — see the
correction box above, not `.env.production`):

```
SUPERVISOR_URL=http://100.119.95.105:8090
SUPERVISOR_TOKEN=<same value as the laptop's ops/supervisor/.env>
```

Restart the backend, same command as §1.2:

```bash
# [DROPLET]
cd /opt/mypillsafe/repo
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d --force-recreate backend
```

### 2.4 — Ops constraints

- **Sidecar start requires AC power.** `POST /start` returns `422` if the machine is on
  battery and `force=false`; `force=true` bypasses this guard only, never the RAM one.
- **>=3 GB free RAM is never overridable.** Verbatim from `ops/supervisor/README.md`:
  `"422 if free RAM < SUPERVISOR_MIN_FREE_GB (measured value in the message; not
  bypassed by force)."`
- **Full brain health also needs Ollama running**, which the Supervisor does not
  manage — zero mentions of Ollama in its code or docs; it only controls the sidecar on
  port 8100. Ollama's auto-start Startup shortcut was deliberately relocated to
  `D:\Projects\PillSafe\archive\2bdeleted\ollama_startup_shortcut\` (not deleted;
  verified present — `Ollama.lnk`) — note this is **outside the app repo**, two tiers
  above `Production\PillSafe`, not a path under it. Move it back, or start Ollama
  manually, before any demo that needs the full brain stack.
- The three scheduled tasks `\MyPillSafe Sidecar`, `\PillSafe\OllamaHealthCheck`,
  `\BB3_ChunkExport` are currently disabled and **stay disabled** — the Supervisor
  replaces the first of the three; the other two are unrelated to it and simply stay
  off.
- **`llama-server.exe` (Ollama's per-model child process) survives killing both
  `ollama.exe` and `ollama app.exe`** — found MPR1 T18/T20; it must be killed explicitly
  by process name/PID for a genuinely clean teardown, otherwise it keeps holding VRAM
  and roughly 1.8 GB RAM.

---

## 3. Deploy this feature to production

There is no CI/CD in this project. Verbatim from `DEPLOY_GUIDE.md` §13
("Deliberately out of scope"):

> "CI/CD (GitHub Actions → GHCR). The manual build in §4 is deliberate for a
> capstone."

The full walkthrough is `DEPLOY_GUIDE.md` §4 (build/push) and §12 (ship an update) —
this section is the gist plus the two commands this runbook depends on.

Note: `DEPLOY_GUIDE.md` §4 itself still shows `cd D:\Projects\PillSafe\PillSafe`,
which predates the 2026-08-15/16 root restructure into five tiers. The current,
correct app-repo path is `D:\Projects\PillSafe\Production\PillSafe`, used below
(that file is not edited here — this note only flags it for whoever follows it).

**[LAPTOP]** — build and push a new backend image, tagged with a timestamp (§4):

```powershell
# [LAPTOP]
cd D:\Projects\PillSafe\Production\PillSafe
$TAG = Get-Date -Format "yyyyMMdd-HHmm"
docker build -t ghcr.io/muthuacumen/mypillsafe-backend:$TAG -t ghcr.io/muthuacumen/mypillsafe-backend:latest dev\backend
docker push ghcr.io/muthuacumen/mypillsafe-backend:$TAG
docker push ghcr.io/muthuacumen/mypillsafe-backend:latest
```

**[DROPLET]** — pull the new code, swap the tag in, restart (§12):

```bash
# [DROPLET]
cd /opt/mypillsafe/repo && sudo git pull
sudo sed -i "s/^IMAGE_TAG=.*/IMAGE_TAG=<new_tag>/" .env
sudo docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml --env-file .env up -d
```

Pulling the new image itself is implicit — `pull_policy: always` is set on the
`backend`/`frontend` services in `docker-compose.prod.yml`, so there's no separate
`docker compose pull` step. See `DEPLOY_GUIDE.md` §4 and §12 for the full sequence,
including the sidecar-restart caveat for any change that touches the brains packages.

---

## 4. Localhost admin

A local dev admin account already exists for testing this feature before it touches
production:

| Field | Value |
|---|---|
| Email | `muthuraj.jayakumar@gmail.com` |
| Password | `<set-locally -- value preserved in archive\2bdeleted\2026-08-20_selfcontained_promotion\redacted_secrets_local_note.md>` (temporary — **change after first login**) |
| Role / flags | `role=ADMIN`, `is_active=true`, `is_verified=true` |
| DB | `Production\PillSafe\dev\backend\pillsafe.db` (local SQLite) |

Verified end-to-end locally this session: login → `200`, `GET /api/v1/admin/stats` →
`200`.

The localhost admin can also start/stop the sidecar from the Admin Panel using a
"Localhost (dev)" profile with **no extra configuration** — the backend's
sidecar-proxy routes (`admin_sidecar.py`) already default `SUPERVISOR_URL` to
`http://127.0.0.1:8090`, which is exactly the local Supervisor's own default bind
(§2.1), so this profile works as soon as the Supervisor is running locally.

---

## 5. Terminating user sessions

Three admin endpoints in `app/api/v1/routes/admin.py`:

| Endpoint | Effect |
|---|---|
| `PUT /api/v1/admin/users/{user_id}/deactivate` (~line 79) | Deactivates the account **and** bumps `token_version` immediately, invalidating every live session/token for that user right away |
| `POST /api/v1/admin/users/{user_id}/terminate-sessions` (~line 100) | Kills live sessions via the same `token_version` bump, **without** deactivating — the user can log back in immediately and get a fresh session |
| `PUT /api/v1/admin/users/{user_id}/activate` (~line 68) | Reactivates a deactivated account |

**New behavior worth flagging:** deactivating a user now also kills their live
sessions immediately (the `token_version` bump), not just a login-time gate as
before — every authenticated request checks `token_version`, so an active session
dies mid-use the moment an admin deactivates the account, not only on that user's
next login attempt.

---

## See also

- `DEPLOY_GUIDE.md` §7.2a — the `ADMIN_EMAILS` mechanism in full context
- `DEPLOY_GUIDE.md` §4 and §12 — full build/push/ship walkthrough
- `DEPLOY_GUIDE.md` §11 — triage table for deploy failures
- `DEPLOY_GUIDE_M1_TwoStageReader.md` — the psql / `docker exec` one-off precedent §1.4 follows
- `postrestartchecklist.md` — laptop reboot / sidecar-restart checklist (Steps 1-4,
  6); its only droplet-facing step is Step 5, a read-only reach check from the
  droplet to the laptop's sidecar — it is not a droplet-restart doc
- `ops/supervisor/README.md` — full HTTP contract for every Supervisor endpoint
