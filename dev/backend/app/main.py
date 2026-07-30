import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import engine, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

_OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": (
            "Register, login, logout, refresh token, "
            "and get current user (`/me`)."
        ),
    },
    {
        "name": "patients",
        "description": (
            "Patient profile management for the authenticated user."
        ),
    },
    {
        "name": "analyze",
        "description": (
            "Upload a medication image and receive AI-powered analysis. "
            "`/analyze/pill/v2` is the pill-scan endpoint — IMB1 (vision) + "
            "SB2 (deterministic verify/reject/abstain matcher) via the "
            "brains sidecar (Priority 6 / Phase 3)."
        ),
    },
    {
        "name": "prescriptions",
        "description": (
            "Prescription label OCR capture and My Medications CRUD "
            "(Priority 1). All endpoints scoped to the authenticated patient."
        ),
    },
    {
        "name": "scans",
        "description": "Read-only Safety Records — past scan history with prescription match status.",
    },
    {
        "name": "contact",
        "description": "Public contact form submission — no auth required.",
    },
    {
        "name": "admin",
        "description": (
            "**Admin only.** Platform stats, user management, "
            "and analysis audit log."
        ),
    },
    {
        "name": "health",
        "description": "Liveness probe — no auth required.",
    },
    {
        "name": "dev",
        "description": (
            "**Development only** — all endpoints here return 404 in "
            "production. Use `/dev/seed-admin` to bootstrap the first "
            "admin account."
        ),
    },
]

_DESCRIPTION = (
    "## Authentication\n\n"
    "1. Call **POST /api/v1/auth/register** or "
    "**POST /api/v1/auth/login** to get an `access_token`.\n"
    "2. Click **Authorize** (🔒) at the top of this page.\n"
    "3. Paste the token into the **Value** field "
    "(just the token — no `Bearer ` prefix needed here).\n"
    "4. Click **Authorize**, then **Close**. "
    "All secured endpoints will now include your token.\n\n"
    "Access tokens expire in **60 minutes**. "
    "Use **POST /api/v1/auth/refresh** to get a new one."
)


@asynccontextmanager
async def lifespan(app_instance: FastAPI):  # noqa: RUF029
    logger.info("PillSafe API starting — initialising database")
    await init_db()
    logger.info("Database ready")
    yield
    logger.info("PillSafe API shutting down")
    await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(
        title="MyPillSafe API",
        version=settings.APP_VERSION,
        description=_DESCRIPTION,
        openapi_tags=_OPENAPI_TAGS,
        docs_url="/docs" if settings.OPENAPI_ENABLED else None,
        redoc_url="/redoc" if settings.OPENAPI_ENABLED else None,
        swagger_ui_parameters=(
            {"persistAuthorization": True}
            if settings.OPENAPI_ENABLED
            else None
        ),
        lifespan=lifespan,
    )

    # Allow :5173 (Vite default) and :5174 (Vite auto-fallback)
    allowed_origins = list(
        {settings.FRONTEND_ORIGIN, "http://localhost:5173", "http://localhost:5174"}
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Compresses JSON responses — cuts bandwidth/latency for larger payloads
    # (prescription lists, OCR/analysis results) under concurrent load.
    application.add_middleware(GZipMiddleware, minimum_size=500)

    application.include_router(api_router)

    @application.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "version": settings.APP_VERSION}

    return application


app = create_app()
