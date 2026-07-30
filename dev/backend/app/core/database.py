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
    """Additive, code-first column sync for SQLite dev DBs.

    `create_all` only creates missing tables — it never alters existing
    ones. New nullable/defaulted columns added to a model after the table
    already exists on disk need an explicit ALTER TABLE here.
    """
    if not settings.DATABASE_URL.startswith("sqlite"):
        return
    column_defs = {
        "patients": [
            ("notifications_enabled", "BOOLEAN NOT NULL DEFAULT 1"),
        ],
        "prescriptions": [
            ("frequency_type", "VARCHAR(30)"),
            ("with_food", "BOOLEAN NOT NULL DEFAULT 0"),
            ("purpose", "VARCHAR(100)"),
            ("max_daily_dose", "INTEGER"),
            ("din", "VARCHAR(8)"),
            ("din_confirmed", "BOOLEAN NOT NULL DEFAULT 0"),
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
        result = await conn.exec_driver_sql(f"PRAGMA table_info({table})")
        existing = {row[1] for row in result.fetchall()}
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
