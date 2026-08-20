# ── Stage 1: Node builder ──────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .

# Build-time feature flag (MPR1-T34pre, dev/frontend/src/lib/featureFlags.ts).
# DEFAULT ABSENT so existing builds are byte-for-byte unchanged -- Vite only
# exposes it to import.meta.env when the ARG is actually passed at build
# time (`--build-arg VITE_TRAY_CHECK=on`), and featureFlags.ts treats
# anything other than the literal string "on" as off. ENV re-exports the ARG
# into the build environment so the `npm run build` (vite build) step below
# can see it -- an ARG alone is not visible to RUN unless promoted this way.
ARG VITE_TRAY_CHECK
ENV VITE_TRAY_CHECK=$VITE_TRAY_CHECK

RUN npm run build
# Output will be at /app/dist

# ── Stage 2: Nginx static server ───────────────────────────────────────────────
FROM nginx:1.25-alpine AS runtime

# Copy built React SPA
COPY --from=builder /app/dist /usr/share/nginx/html

# NOTE: the SPA-routing nginx config (docker/nginx/spa.conf) is intentionally
# NOT copied here — it lives outside this build context (dev/frontend) and
# Docker cannot COPY files from outside its context. docker-compose.yml mounts
# it in at runtime instead (same pattern already used for the gateway's own
# nginx.conf/default.conf), so it stays editable without an image rebuild.

EXPOSE 80

# Probe 127.0.0.1 (not `localhost`): inside the container `localhost` resolves
# to IPv6 ::1 first, but nginx `listen 80;` binds IPv4 only, so a localhost
# probe gets "connection refused" and marks a perfectly-serving container
# unhealthy. 127.0.0.1 forces IPv4 and matches where nginx actually listens.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
