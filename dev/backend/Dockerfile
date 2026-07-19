# ── Stage 1: builder ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-optional.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    # requirements-optional.txt installs PaddleOCR — real prescription-label
    # reading. Without it, OCR_PIPELINE_ENABLED silently falls back to demo
    # text for every upload regardless of image content (see ocr_service.py).
    && pip install --no-cache-dir -r requirements-optional.txt \
    # paddle eagerly imports paddle.utils.cpp_extension at package-init time,
    # which pulls in Cython's compiled internals — Cython 3.x segfaults on
    # import in this stack (observed: SIGSEGV inside Cython.Compiler.Errors).
    # Pin back to the 0.29.x line, which doesn't have this binary-compat issue.
    && pip install --no-cache-dir "cython<3.0"

# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

WORKDIR /app

# Runtime system deps only
# libgomp1 is required by paddlepaddle's compiled core (libpaddle.so links
# against libgomp.so.1) — without it, paddle fails to import at all and OCR
# silently falls back to demo text.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    zlib1g \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# libpaddle.so statically bundles its own copy of zlib and exports those
# symbols globally (confirmed via `nm -D libpaddle.so`), which silently
# hijacks every other library's zlib calls process-wide once paddle is
# imported — any later-loaded compiled extension that also calls
# inflate/inflateReset2 (pyclipper, scipy._lib._ccallback_c, ...) gets routed
# to paddle's bundled copy instead of the real system zlib and fails with
# "zlib.error: Error -2 while decompressing data: inconsistent stream state"
# (or segfaults outright). Preloading the real libz.so.1 first forces the
# dynamic linker to resolve those symbols to it instead. Not a PillSafe bug —
# a symbol-visibility defect in the upstream paddlepaddle 2.6.2 wheel.
ENV LD_PRELOAD=/lib/x86_64-linux-gnu/libz.so.1

# Non-root user for security
RUN adduser --disabled-password --gecos "" pillsafe && chown -R pillsafe /app
USER pillsafe

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
