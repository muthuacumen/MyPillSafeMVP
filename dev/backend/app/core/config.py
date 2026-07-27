from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Look for .env in current dir or one level up (project root)
    model_config = SettingsConfigDict(
        env_file=[".env", "../.env", "../../.env"],
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = "development"
    APP_VERSION: str = "0.1.0"
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # SQLite — file lives next to backend/
    DATABASE_URL: str = "sqlite+aiosqlite:///./pillsafe.db"

    FRONTEND_ORIGIN: str = "http://localhost:5173"

    OPENAPI_ENABLED: bool = True
    ML_PIPELINE_ENABLED: bool = False
    # Real PaddleOCR prescription parsing. Was left off by default, which meant
    # every upload silently returned canned demo text regardless of the image —
    # keep this on so a fresh clone (no .env override) doesn't regress into
    # that bug again.
    OCR_PIPELINE_ENABLED: bool = True

    # CB4 (Phase 4) -- the production voice for BB3 Q&A, app/services/cb4_service.py.
    # Cloud call ONLY when LLM_API_KEY is non-empty (client constructed lazily);
    # no key -> the sidecar's mode="full" local-7B offline fallback is used instead.
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "claude-haiku-4-5"

    UPLOAD_DIR: str = "./uploads"

    # Brains sidecar (Phase 1 of the app x brains integration) -- a separate
    # FastAPI microservice (dev/brains/) that hosts the frozen IMB1_v0 +
    # SB2 packages. `/analyze/pill/v2` (app/api/v1/routes/pill.py) is the
    # ONLY pill-scan endpoint as of Phase 3 -- the legacy OpenCV path was
    # removed entirely, so this flag is now a pure kill-switch (default ON;
    # set to false only if the sidecar can't be run on this deployment).
    BRAINS_SERVICE_URL: str = "http://127.0.0.1:8100"
    PILL_V2_ENABLED: bool = True

    # Sidecar pool (Task A3, deploy-readiness build): comma-separated URLs for
    # a team of laptop-hosted sidecars, health-checked so a closed laptop
    # doesn't take the demo down. Empty (the default) is the back-compat
    # single-sidecar path -- `brains_registry.resolve_brains_url()` returns
    # BRAINS_SERVICE_URL directly with NO health check in that case, so every
    # existing dev setup / test stays byte-identical in behaviour and latency.
    BRAINS_SERVICE_URLS: str = ""


settings = Settings()
