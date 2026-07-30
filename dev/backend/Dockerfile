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
    # FixbySonnet1 Task 5: requirements-optional.txt now installs only the
    # Claude SDK (CB4) -- faster-whisper (assistant voice input) was removed
    # with the assistant widget; see that file's header.
    && pip install --no-cache-dir -r requirements-optional.txt

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps only.
# FixbySonnet1 Task 5: libgomp1 was faster-whisper's ctranslate2 backend
# (assistant voice input, Priority 5) -- that dependency is gone with the
# assistant widget (requirements-optional.txt no longer lists it), and
# nothing else in the installed set links against libgomp.so.1. Verified by
# building this image and running the full backend suite inside it (110
# passed) both with and without this package -- see Builder Report.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
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
