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

    # --- Registration gating -------------------------------------------------
    # Every new signup lands inactive and an admin approves it. Deliberately
    # rides on the EXISTING `users.is_active` column rather than a new
    # `approval_status` one: this project is code-first with no migrations, and
    # `create_all` never ALTERs an existing table -- a column added to the model
    # but never to Postgres raises UndefinedColumn on every read AND write while
    # every health check stays green. That is exactly what took the live site
    # down on 2026-07-30. `is_active` already exists in production and already
    # means "may this account authenticate", which is the whole question here.
    #
    # false is the kill-switch: registration goes back to today's behaviour
    # (201 + tokens + refresh cookie, account active immediately).
    REQUIRE_ADMIN_APPROVAL: bool = True
    # Comma-separated, case-insensitive. Every matching EXISTING user is
    # promoted to ADMIN and reactivated at boot (app/services/admin_bootstrap).
    # This is the only way to mint an admin in production -- /dev/seed-admin
    # 404s unless APP_ENV == "development".
    ADMIN_EMAILS: str = ""

    # --- Outbound mail (contact form) ---------------------------------------
    # Inert by default: a blank SMTP_HOST/SMTP_USER/SMTP_PASSWORD makes
    # mail_service return False without opening a socket, so the app ships and
    # runs with no credentials at all. Filling these in is what turns the
    # /contact notification on -- the JSONL log is written either way and is
    # still the system of record.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_STARTTLS: bool = True
    CONTACT_TO: str = "info@mypillsafe.ca"

    OPENAPI_ENABLED: bool = True
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

    # --- Tray scan (MPR1-T04) ------------------------------------------------
    # `/api/v1/tray/analyze` proxies the sidecar's `/tray/analyze`. Pure
    # kill-switch, same shape as PILL_V2_ENABLED: off -> 501.
    #
    # DEFAULT OFF, and unlike PILL_V2_ENABLED it stays off until someone turns
    # it on. The production sidecar does not serve `/tray/analyze` yet, so
    # default-on meant the next routine deploy exposed tray scanning to real
    # patients against a sidecar that cannot answer -- a feature shipped by
    # forgetting rather than by deciding. Set TRAY_ANALYZE_ENABLED=true on a
    # deployment whose sidecar actually has the route.
    TRAY_ANALYZE_ENABLED: bool = False
    # Server default for the tray NONE (no markings on any photographed face)
    # route: "retry" -> Flip/Reshoot alongside Unreadable, which is Muthu's
    # filed tray call (3); "terminal" -> the single-pill v3 1.8 message.
    #
    # WHETHER THE RETRY LOOP SHOULD EVER BECOME TERMINAL IS PENDING WITH MUTHU
    # (a pill blank on BOTH faces would otherwise loop forever). Both routes
    # are built and the request may override this per call, so the choice can
    # be made later without touching the verdict layer. Do not "resolve" this
    # by deleting a branch.
    TRAY_NONE_ROUTE: str = "retry"

    # Sidecar pool (Task A3, deploy-readiness build): comma-separated URLs for
    # a team of laptop-hosted sidecars, health-checked so a closed laptop
    # doesn't take the demo down. Empty (the default) is the back-compat
    # single-sidecar path -- `brains_registry.resolve_brains_url()` returns
    # BRAINS_SERVICE_URL directly with NO health check in that case, so every
    # existing dev setup / test stays byte-identical in behaviour and latency.
    BRAINS_SERVICE_URLS: str = ""

    # --- Rx parsing (FixbyOPUS3) --------------------------------------------
    # The medication PROPOSER is swappable behind these two values; the
    # guardrails (app/services/rx_guardrails.py) and the server-side reminder
    # -time derivation are proposer-agnostic and ALWAYS apply, so flipping
    # either flag changes who proposes, never which safety rules run.
    #
    # RX_LLM_PARSE_ENABLED=false is the kill-switch: the deterministic regex
    # parser proposes instead, still guarded, still derived. It is also what
    # happens automatically whenever the sidecar or Ollama is unreachable --
    # honest degradation, never a fabricated prescription.
    RX_LLM_PARSE_ENABLED: bool = True
    # 'qwen' -> the sidecar's local qwen2.5:7b-instruct (Muthu's durable
    # 2026-07-28 model decision: self-contained, zero marginal cost).
    # 'regex' -> skip the LLM entirely, same as RX_LLM_PARSE_ENABLED=false.
    # A future 'haiku' value is DOCUMENTED, not implemented: Claude Haiku 4.5
    # measured strictly better on the 2026-07-28 evaluation (12/12 labels,
    # 50/50 fields, 0 safety events vs qwen's 11/12, 49/50, 0) and is recorded
    # as a finding -- see documentation/evaluation/rx_parsing/README.md.
    RX_PARSE_BACKEND: str = "qwen"


settings = Settings()
