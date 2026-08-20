from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

_connect_args = {"check_same_thread": False} if _is_sqlite else {}

# SQLite has no real connection pool (one file, no concurrent-writer benefit
# from pooling), so pool sizing only applies to Postgres in production, where
# it directly determines how many requests can hit the DB at once under load.
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size": 20,
        "max_overflow": 20,
        "pool_pre_ping": True,
        "pool_recycle": 1800,
    }
)

engine = create_async_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.APP_ENV == "development",
    **_pool_kwargs,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def _add_missing_columns(conn) -> None:
    """Additive, code-first column sync for SQLite dev DBs AND Postgres.

    `create_all` only creates missing tables — it never alters existing
    ones. New nullable/defaulted columns added to a model after the table
    already exists on disk need an explicit ALTER TABLE here.

    This used to return early on any non-SQLite URL, which took the
    production site down on 2026-07-30: the `prescriptions` table had been
    created by `create_all` on 2026-07-27 (commit 115f8ba), commit b969487
    added `pill_verifiable` / `review_status` / `parse_source` /
    `parse_flags` to the model, and nothing ever added them to Postgres.
    Every SELECT and INSERT naming those columns failed with
    UndefinedColumn, so `GET /prescriptions/me` returned 500 (breaking My
    Medications AND the 30 s dose-reminder poll) and every Rx scan died
    immediately after its three healthy sidecar calls. The one-shot repair
    for the already-broken database is `docker/fix_prescriptions_schema.sql`;
    this function is what stops it recurring on the next column addition.

    Dialect differences that matter here, both learned the hard way:
      * introspection — SQLite has `PRAGMA table_info`, Postgres has
        `information_schema.columns`; neither understands the other.
      * boolean literals — SQLite wants `1`/`0`, Postgres rejects those for
        a BOOLEAN column and wants `TRUE`/`FALSE`. Rendering the wrong one
        fails on the first boolean column, so the literal is chosen per
        dialect rather than hardcoded.
    """
    dialect = conn.dialect.name
    if dialect not in ("sqlite", "postgresql"):
        # Nothing else is a supported target; stay silent rather than emit
        # DDL in a syntax we have not verified.
        return
    is_sqlite = dialect == "sqlite"
    true_lit, false_lit = ("1", "0") if is_sqlite else ("TRUE", "FALSE")
    column_defs = {
        "users": [
            # Task T2 -- real session termination. 0 for every existing row,
            # matching the model's default, so no pre-existing token is
            # invalidated by the ALTER itself.
            ("token_version", "INTEGER NOT NULL DEFAULT 0"),
        ],
        "patients": [
            ("notifications_enabled", f"BOOLEAN NOT NULL DEFAULT {true_lit}"),
        ],
        "prescriptions": [
            ("frequency_type", "VARCHAR(30)"),
            ("with_food", f"BOOLEAN NOT NULL DEFAULT {false_lit}"),
            ("purpose", "VARCHAR(100)"),
            ("max_daily_dose", "INTEGER"),
            ("din", "VARCHAR(8)"),
            ("din_confirmed", f"BOOLEAN NOT NULL DEFAULT {false_lit}"),
            # FixbyOPUS3 Task A3 -- the review workflow. The DDL default is
            # 'pending' (what a NEW row must be); pre-existing rows are
            # backfilled to 'approved' immediately below, because they were
            # created before a review screen existed and demoting them would
            # switch off a working user's reminders.
            ("review_status", "VARCHAR(16) NOT NULL DEFAULT 'pending'"),
            ("parse_source", "VARCHAR(16)"),
            ("parse_flags", "VARCHAR(255)"),
            # FixbyOPUS3 Task B3 -- NULL means "not established", never False.
            ("pill_verifiable", "BOOLEAN"),
        ],
        "analyses": [
            # Phase 3 (pill-scan v2) -- see app/models/analysis.py.
            ("detected", "BOOLEAN"),
            ("decision", "VARCHAR(20)"),
            ("abstain_action", "VARCHAR(20)"),
            ("matched_din", "VARCHAR(8)"),
            ("top_candidate_score", "FLOAT"),
            ("top_candidate_breakdown", "JSON"),
            ("shadow_fusion_suspected", "BOOLEAN"),
        ],
    }
    for table, columns in column_defs.items():
        if is_sqlite:
            result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
            existing = {row[1] for row in result.fetchall()}
        else:
            result = await conn.exec_driver_sql(
                "SELECT column_name FROM information_schema.columns "
                f"WHERE table_schema = current_schema() AND table_name = '{table}'"
            )
            existing = {row[0] for row in result.fetchall()}
        for name, ddl_type in columns:
            if name not in existing:
                await conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {name} {ddl_type}")
                if table == "prescriptions" and name == "review_status":
                    # One-time grandfathering, run ONLY on the ALTER (never on
                    # a boot where the column already existed, which would
                    # bulk-approve every genuinely pending proposal).
                    await conn.exec_driver_sql(
                        "UPDATE prescriptions SET review_status = 'approved'"
                    )

    # ALTER TABLE ADD COLUMN never creates an index -- add it explicitly
    # (idempotent) so pre-existing dev DBs get the same indexes that
    # `create_all` would give a fresh one.
    await conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_prescriptions_din ON prescriptions (din)"
    )
    await conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_analyses_decision ON analyses (decision)"
    )
    await conn.exec_driver_sql(
        "CREATE INDEX IF NOT EXISTS ix_analyses_matched_din ON analyses (matched_din)"
    )


async def init_db() -> None:
    """Create all tables from models (code-first, run on startup).

    Note: `app.models.din_pill` (the `din_pills` table, Priority 6's
    OpenCV-era DIN lookup) is intentionally no longer imported here as of
    Phase 3 -- that model/table was retired with the legacy OpenCV pill
    path. Any pre-existing `din_pills` table on a dev DB is left in place
    (this sync is additive-only, never drops) but is now orphaned.
    """
    import app.models.user  # noqa: F401
    import app.models.patient  # noqa: F401
    import app.models.analysis  # noqa: F401
    import app.models.prescription  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await _add_missing_columns(conn)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
