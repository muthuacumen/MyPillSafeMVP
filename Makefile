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
