# ── Stage 1: builder ──────────────────────────────────────────────────────────
# Task A4 (deploy-readiness build): PaddleOCR/PaddlePaddle no longer live in
# this image at all -- prescription OCR is a remote call to the `dev/brains`
# sidecar over the tailnet (see app/services/ocr_service.py). That removed
# ~3 GB and every paddle-only apt package / pip pin below (LD_PRELOAD zlib
# workaround, the cython<3.0 pin, libgl1/libglib2.0-0). See A4 report for the
# measured before/after image size.
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # requirements-optional.txt now installs only the Claude SDK (CB4) and
    # faster-whisper (assistant voice input) -- see that file's header.
    && pip install --no-cache-dir -r requirements-optional.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps only.
# libgomp1 is a real, still-needed dependency: faster-whisper's ctranslate2
# backend (assistant voice input, Priority 5) uses OpenMP and links against
# libgomp.so.1 -- keep it even though paddle (its original reason for being
# here) is gone.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# Non-root user for security
RUN adduser --disabled-password --gecos "" pillsafe && chown -R pillsafe /app
USER pillsafe

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
