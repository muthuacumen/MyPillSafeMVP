# ──────────────────────────────────────────────────────────────────────────────
# Docker targets — PillSafe full stack
# ──────────────────────────────────────────────────────────────────────────────

COMPOSE = docker compose -f docker/docker-compose.yml --env-file .env

## Start full Docker stack (builds images on first run)
dev:
	$(COMPOSE) up --build

## Start in background (detached)
dev-bg:
	$(COMPOSE) up --build -d

## Stop all containers (data volumes preserved)
down:
	$(COMPOSE) down

## Stop AND wipe all data volumes (full reset)
reset:
	$(COMPOSE) down -v

## Show live logs (all services)
logs:
	$(COMPOSE) logs -f

## Show logs for one service: make logs-s s=backend
logs-s:
	$(COMPOSE) logs -f $(s)

## Run backend pytest suite inside container
test:
	$(COMPOSE) exec backend pytest tests/ -v --tb=short

## Open psql shell inside postgres container
db-shell:
	$(COMPOSE) exec postgres psql -U pillsafe_user -d pillsafe

## Open redis-cli inside redis container
redis-shell:
	$(COMPOSE) exec redis redis-cli

## Check health of all containers
status:
	$(COMPOSE) ps

## Rebuild a single service: make rebuild s=backend
rebuild:
	$(COMPOSE) up --build -d $(s)

# ──────────────────────────────────────────────────────────────────────────────
# Local (non-Docker) dev targets — the real day-to-day run story on this
# machine (Windows 11 + RTX 4060). The brains sidecar is never containerized
# (see docker/docker-compose.yml's comment block: host GPU/CUDA + the frozen
# IMB1_v0/SB2/BB3 sibling packages live outside the repo). Run in three
# terminals, in order: brains -> backend -> frontend. Full detail + seeded
# test accounts: documentation/integration/LOCAL_TESTING.md
# ──────────────────────────────────────────────────────────────────────────────

## Brains sidecar (IMB1 + SB2 + BB3) on :8100 -- own venv, start FIRST
brains:
	cd dev/brains && ./.venv/Scripts/python.exe -m uvicorn app:app --host 127.0.0.1 --port 8100

## App backend (FastAPI) on :8000 -- own venv, start SECOND
backend:
	cd dev/backend && ./venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

## Frontend (Vite dev server) on :5173 -- start THIRD
frontend:
	cd dev/frontend && npm run dev

## Backend pytest suite in the LOCAL venv (not the Docker container)
test-backend:
	cd dev/backend && ./venv/Scripts/python.exe -m pytest tests/ -q

## Seeded test accounts + suggested flows -- see LOCAL_TESTING.md (the seed
## script itself is a session scratchpad artifact, not yet committed to the repo)
seed:
	@echo "Test accounts + suggested test flows: documentation/integration/LOCAL_TESTING.md"
