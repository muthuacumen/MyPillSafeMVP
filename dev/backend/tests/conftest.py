import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.main import app as fastapi_app
from app.core.config import settings
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.models.user import User, UserRole
import app.models.patient  # noqa: F401
import app.models.analysis  # noqa: F401
import app.models.prescription  # noqa: F401

TEST_DB_URL = "sqlite+aiosqlite:///./pillsafe_test.db"

test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
TestSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(autouse=True)
def _ocr_pipeline_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    """Task A2.2: prescription OCR now calls a real HTTP sidecar
    (`ocr_service.extract_text`) instead of an in-process PaddleOCR engine
    that gracefully degraded to demo text whenever `paddleocr` wasn't
    installed (as it isn't in this test venv) -- so most tests, which only
    care that a prescription upload succeeds and don't care what OCR said,
    would otherwise depend on a live sidecar being reachable at
    `BRAINS_SERVICE_URL`. Default every test to the explicit
    `OCR_PIPELINE_ENABLED=false` local-dev demo-text path instead; tests that
    exercise real OCR behaviour (test_prescriptions.py) explicitly
    re-enable it and mock `ocr_service.extract_text` directly.
    """
    monkeypatch.setattr(settings, "OCR_PIPELINE_ENABLED", False)


@pytest.fixture(autouse=True)
def _rx_llm_parse_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    """FixbyOPUS3: prescription create now also calls the sidecar's
    `/rx/extract` (local qwen). Same hermeticity problem as OCR above, but
    sharper -- if a sidecar happens to be running on this machine the suite
    would silently start measuring a 7B model's opinions, and the same test
    would pass or fail depending on whether someone had a service up.
    (Measured, not hypothetical: two prescription tests failed exactly this
    way during this build while the sidecar was live.)

    Default every test to the deterministic regex proposer. The guardrails
    and the server-side time derivation still run -- they are proposer-
    agnostic by design -- so this switches off the model, never the safety
    layer. Tests that exercise the LLM path (test_rx_review_flow.py) turn
    the flag back on and mock `rx_extract_service.extract_medications`.
    """
    monkeypatch.setattr(settings, "RX_LLM_PARSE_ENABLED", False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    async def override_get_db():
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    fastapi_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def approve_user(db_session: AsyncSession):
    """Do what an admin's Approve button does: flip `is_active` to True.

    Registration is admin-gated by default now (REQUIRE_ADMIN_APPROVAL), so
    /register no longer hands back a token. Every test that just needs "a
    signed-in patient" wants the POST-approval state, and the honest way to
    get there is to approve — NOT to switch REQUIRE_ADMIN_APPROVAL off in a
    global fixture, which would run the entire suite against a configuration
    production does not use and leave the shipped path covered by only a
    handful of tests.
    """
    async def _approve(email: str) -> User:
        result = await db_session.execute(select(User).where(User.email == email))
        user = result.scalar_one()
        user.is_active = True
        await db_session.flush()
        return user

    return _approve


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, approve_user) -> str:
    """Register a fresh patient account, approve it, return an access token."""
    email = f"patient_{uuid.uuid4().hex[:10]}@pillsafe.dev"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Test1234",
            "first_name": "Test",
            "last_name": "Patient",
            "date_of_birth": "1990-01-01",
        },
    )
    user = await approve_user(email)
    return create_access_token(user.id, user.role)


@pytest_asyncio.fixture
async def auth_headers(auth_token: str) -> dict:
    return {"Authorization": f"Bearer {auth_token}"}


@pytest_asyncio.fixture
async def admin_headers(client: AsyncClient, db_session: AsyncSession) -> dict:
    """Register a normal account then promote it to ADMIN directly in the DB.

    Deliberately doesn't go through /dev/seed-admin — that endpoint 404s
    outside APP_ENV=development, which CI does not run with. `is_active` is
    set here too, for the same reason approve_user exists: registration is
    admin-gated, so a freshly registered account is inactive and
    get_current_user would reject its token.
    """
    email = f"admin_{uuid.uuid4().hex[:10]}@pillsafe.dev"
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "Admin1234",
            "first_name": "Admin",
            "last_name": "Test",
            "date_of_birth": "1990-01-01",
        },
    )
    result = await db_session.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.role = UserRole.ADMIN.value
    user.is_active = True
    await db_session.flush()
    token = create_access_token(user.id, user.role)
    return {"Authorization": f"Bearer {token}"}
