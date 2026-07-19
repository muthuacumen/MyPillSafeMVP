# ── Stage 1: Node builder ──────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package*.json ./
RUN npm ci --prefer-offline

COPY . .
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

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
