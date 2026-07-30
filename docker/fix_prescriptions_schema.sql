-- One-shot production schema repair (2026-07-30).
--
-- WHY: production's `prescriptions` table was created by `create_all` on
-- 2026-07-27 from commit 115f8ba. Commit b969487 (rolled forward 2026-07-30)
-- added four columns to the model -- pill_verifiable, review_status,
-- parse_source, parse_flags -- but nothing added them to Postgres:
-- `create_all` never alters an existing table, and the boot-time sync in
-- app/core/database.py returned early on any non-SQLite URL. Every SELECT and
-- INSERT naming those columns therefore failed with UndefinedColumn, which is
-- why GET /prescriptions/me returned 500 and every Rx scan died immediately
-- after the (healthy) sidecar calls.
--
-- This script is idempotent and additive-only -- it never drops or retypes a
-- column, so it is safe to re-run. It covers every column the boot-time sync
-- knows about, not just the four above, in case this volume predates 115f8ba.
-- Booleans use TRUE/FALSE, not the sync's SQLite-only 1/0 literals.
--
-- RUN:  docker exec -i pillsafe_postgres psql -U pillsafe_user -d pillsafe \
--         < docker/fix_prescriptions_schema.sql
--
-- The permanent fix (a dialect-aware boot-time sync) ships in
-- app/core/database.py; this script is what unblocks the running site now.

BEGIN;

-- patients ------------------------------------------------------------------
ALTER TABLE patients
    ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE;

-- prescriptions -------------------------------------------------------------
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS frequency_type   VARCHAR(30);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS with_food        BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS purpose          VARCHAR(100);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS max_daily_dose   INTEGER;
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS din              VARCHAR(8);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS din_confirmed    BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS parse_source     VARCHAR(16);
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS parse_flags      VARCHAR(255);
-- NULL means "not established" (sidecar down at confirm time), never False.
ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS pill_verifiable  BOOLEAN;

-- review_status needs the grandfathering rule, so it cannot use a bare
-- ADD COLUMN IF NOT EXISTS: the DDL default is 'pending' (correct for a NEW
-- row), but every row that already exists predates the review screen and is
-- already live in someone's medication list. Demoting those to 'pending'
-- would switch off a working user's dose reminders, so they backfill to
-- 'approved' -- and that backfill must run ONLY on the boot that actually
-- adds the column, never on a re-run, or it would bulk-approve genuinely
-- pending proposals. Hence the guarded DO block.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name   = 'prescriptions'
          AND column_name  = 'review_status'
    ) THEN
        ALTER TABLE prescriptions
            ADD COLUMN review_status VARCHAR(16) NOT NULL DEFAULT 'pending';
        UPDATE prescriptions SET review_status = 'approved';
        RAISE NOTICE 'review_status added; % pre-existing row(s) grandfathered to approved',
            (SELECT count(*) FROM prescriptions);
    ELSE
        RAISE NOTICE 'review_status already present -- no backfill (correct)';
    END IF;
END $$;

-- analyses ------------------------------------------------------------------
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS detected                 BOOLEAN;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS decision                 VARCHAR(20);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS abstain_action           VARCHAR(20);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS matched_din              VARCHAR(8);
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS top_candidate_score      FLOAT;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS top_candidate_breakdown  JSON;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS shadow_fusion_suspected  BOOLEAN;

-- Indexes ADD COLUMN never creates -----------------------------------------
CREATE INDEX IF NOT EXISTS ix_prescriptions_din  ON prescriptions (din);
CREATE INDEX IF NOT EXISTS ix_analyses_decision  ON analyses (decision);
CREATE INDEX IF NOT EXISTS ix_analyses_matched_din ON analyses (matched_din);

COMMIT;

-- Verification: all four of the columns that broke the site must appear.
\echo ''
\echo '=== prescriptions: the four columns from b969487 ==='
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = current_schema()
  AND table_name = 'prescriptions'
  AND column_name IN ('pill_verifiable', 'review_status', 'parse_source', 'parse_flags')
ORDER BY column_name;

\echo ''
\echo '=== review_status distribution (pre-existing rows should be approved) ==='
SELECT review_status, count(*) FROM prescriptions GROUP BY review_status ORDER BY 1;
