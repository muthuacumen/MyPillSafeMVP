"""Boot-time column-sync guards (`app/core/database._add_missing_columns`).

These exist because the sync had NO test coverage at all, and that gap took
the production site down on 2026-07-30. The `prescriptions` table was created
by `create_all` on 2026-07-27 (commit 115f8ba); commit b969487 added
`pill_verifiable` / `review_status` / `parse_source` / `parse_flags` to the
model; the sync bailed out on the first line for any non-SQLite URL, so those
columns were never added to Postgres. Result: UndefinedColumn on every SELECT
and INSERT naming them -- `GET /prescriptions/me` 500 (My Medications AND the
30 s dose-reminder poll), and every Rx scan dying right after three healthy
sidecar calls.

The tests below pin the three things that were wrong or untested:
  1. the sync must actually RUN on postgresql, not just sqlite;
  2. boolean defaults must be rendered in the dialect's own literals
     (`1`/`0` for SQLite, `TRUE`/`FALSE` for Postgres -- Postgres rejects
     `DEFAULT 1` on a BOOLEAN column, so the wrong literal fails on the
     first boolean);
  3. the `review_status` grandfathering must fire ONLY on the boot that
     adds the column -- re-running it would bulk-approve genuinely pending
     proposals, which is a safety regression, not a cosmetic one.

No live database is involved: the DDL is asserted against a recording fake
connection, so these run in the offline suite.
"""
import re

import pytest

from app.core.database import _add_missing_columns

# Every column the models declare for the three synced tables, as of b969487.
# Kept explicit so that adding a model column without registering it in the
# sync's `column_defs` fails the parity test below instead of silently
# breaking the next Postgres deploy.
_MODEL_COLUMNS = {
    "patients": {"notifications_enabled"},
    "prescriptions": {
        "frequency_type", "with_food", "purpose", "max_daily_dose", "din",
        "din_confirmed", "review_status", "parse_source", "parse_flags",
        "pill_verifiable",
    },
    "analyses": {
        "detected", "decision", "abstain_action", "matched_din",
        "top_candidate_score", "top_candidate_breakdown",
        "shadow_fusion_suspected",
    },
}


class _FakeResult:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _FakeDialect:
    def __init__(self, name):
        self.name = name


class _FakeConn:
    """Records every statement and answers introspection from `existing`."""

    def __init__(self, dialect_name, existing=None):
        self.dialect = _FakeDialect(dialect_name)
        self.existing = existing if existing is not None else {}
        self.statements = []

    async def exec_driver_sql(self, sql):
        self.statements.append(sql)
        if sql.startswith("PRAGMA table_info"):
            table = sql.split("(", 1)[1].rstrip(")")
            # PRAGMA puts the column name at index 1.
            return _FakeResult([(i, c) for i, c in enumerate(self.existing.get(table, []))])
        if "information_schema.columns" in sql:
            table = re.search(r"table_name = '([a-z_]+)'", sql).group(1)
            return _FakeResult([(c,) for c in self.existing.get(table, [])])
        return _FakeResult([])

    def alters(self):
        return [s for s in self.statements if s.startswith("ALTER TABLE")]


def _added_columns(conn):
    return {
        m.group(2)
        for m in (re.match(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", s) for s in conn.alters())
        if m
    }


# --- 1. The regression: the sync must run on Postgres ----------------------

@pytest.mark.asyncio
async def test_postgres_dialect_is_not_skipped():
    """The exact 2026-07-30 outage: a Postgres DB whose `prescriptions` table
    predates b969487 must get all four columns added."""
    pre_b969487 = [
        "id", "patient_id", "drug_name", "dosage", "frequency_text",
        "frequency_type", "time_slots", "specific_times", "with_food",
        "purpose", "max_daily_dose", "prescribing_doctor", "refills_remaining",
        "expiry_date", "is_active", "image_path", "din", "din_confirmed",
        "created_at", "updated_at",
    ]
    conn = _FakeConn("postgresql", {"prescriptions": pre_b969487})
    await _add_missing_columns(conn)

    added = _added_columns(conn)
    for column in ("pill_verifiable", "review_status", "parse_source", "parse_flags"):
        assert column in added, f"{column} was not added -- this is the outage"


@pytest.mark.asyncio
async def test_postgres_uses_information_schema_not_pragma():
    conn = _FakeConn("postgresql", {})
    await _add_missing_columns(conn)
    assert any("information_schema.columns" in s for s in conn.statements)
    assert not any(s.startswith("PRAGMA") for s in conn.statements), (
        "PRAGMA table_info is SQLite-only and silently returns nothing on Postgres"
    )


@pytest.mark.asyncio
async def test_sqlite_still_uses_pragma():
    conn = _FakeConn("sqlite", {})
    await _add_missing_columns(conn)
    assert any(s.startswith("PRAGMA table_info") for s in conn.statements)
    assert not any("information_schema" in s for s in conn.statements)


@pytest.mark.asyncio
async def test_unknown_dialect_emits_no_ddl():
    conn = _FakeConn("mysql", {})
    await _add_missing_columns(conn)
    assert conn.statements == []


# --- 2. Boolean literals must be dialect-legal -----------------------------

@pytest.mark.asyncio
async def test_postgres_booleans_use_true_false():
    conn = _FakeConn("postgresql", {})
    await _add_missing_columns(conn)
    boolean_alters = [s for s in conn.alters() if "BOOLEAN NOT NULL" in s]
    assert boolean_alters, "expected at least one defaulted BOOLEAN column"
    for stmt in boolean_alters:
        assert re.search(r"DEFAULT (TRUE|FALSE)", stmt), stmt
        assert not re.search(r"DEFAULT [01]\b", stmt), (
            f"Postgres rejects an integer default on a BOOLEAN column: {stmt}"
        )


@pytest.mark.asyncio
async def test_sqlite_booleans_use_one_zero():
    conn = _FakeConn("sqlite", {})
    await _add_missing_columns(conn)
    boolean_alters = [s for s in conn.alters() if "BOOLEAN NOT NULL" in s]
    assert boolean_alters
    for stmt in boolean_alters:
        assert re.search(r"DEFAULT [01]\b", stmt), stmt


# --- 3. Grandfathering fires exactly once ----------------------------------

@pytest.mark.asyncio
async def test_grandfathering_runs_when_review_status_is_added():
    conn = _FakeConn("postgresql", {"prescriptions": ["id", "drug_name"]})
    await _add_missing_columns(conn)
    assert any(
        "UPDATE prescriptions SET review_status = 'approved'" in s
        for s in conn.statements
    ), "pre-existing rows must be grandfathered or live reminders switch off"


@pytest.mark.asyncio
async def test_grandfathering_skipped_when_review_status_already_exists():
    """Safety-critical: re-running the sync must never bulk-approve proposals
    the patient has not reviewed."""
    conn = _FakeConn("postgresql", {"prescriptions": ["id", "review_status"]})
    await _add_missing_columns(conn)
    assert not any("SET review_status = 'approved'" in s for s in conn.statements)


# --- 4. Parity: no model column may go unregistered ------------------------

@pytest.mark.parametrize("table", sorted(_MODEL_COLUMNS))
@pytest.mark.asyncio
async def test_sync_registers_every_model_column(table):
    """Adding a column to a model without adding it to `column_defs` is the
    defect class that caused the outage -- catch it here, not in production."""
    conn = _FakeConn("postgresql", {})
    await _add_missing_columns(conn)
    registered = {
        m.group(2)
        for m in (re.match(r"ALTER TABLE (\w+) ADD COLUMN (\w+)", s) for s in conn.alters())
        if m and m.group(1) == table
    }
    missing = _MODEL_COLUMNS[table] - registered
    assert not missing, f"{table}: not registered in the boot-time sync: {sorted(missing)}"
