-- ============================================================
-- FILE: isd_subscriptions.sql
-- Purpose: Create and seed the two ISD-specific subscription
--          access-control tables.
--
-- These tables implement fine-grained, per-user subscription
-- visibility for ISD (Information Services Department) users.
-- When a user whose email address belongs to the ISD domain
-- (e.g. user@isd.lacounty.gov) logs in, the portal checks these
-- two tables in priority order and shows only the Azure
-- subscriptions (and/or AWS accounts) the user is permitted
-- to see:
--
--   1. portal.isd_non_support_teams
--        Non-support-team ISD staff.  Each row pairs one email
--        address with one subscription / account ID.  A user sees
--        only the IDs on their own row(s).  The same column holds
--        Azure subscription GUIDs (UUID format) and AWS account
--        IDs (12-digit number) — the portal auto-detects the cloud
--        from the ID format.
--
--   2. portal.isd_linux_windows_team  (type-based access)
--        Linux/Windows team ISD staff.  Each row has a 'type'
--        column (e.g. 'wps' for Windows Platform Services, 'lps'
--        for Linux Platform Services).  When a user's email is
--        found in this table, the portal reads their type and
--        returns ALL subscription / account IDs in the table that
--        share the same type.  This makes the type a shared access
--        group — every member of the same type sees the same set
--        of resources.  As with table 1, the same column holds
--        Azure and AWS IDs; the portal filters by format.
--
-- Priority rule:
--   The portal checks table 1 first.  If the email is found
--   there, table 2 is not consulted.  For non-ISD users this
--   entire logic is skipped.
--
-- Usage:
--   1. Run this script once against your Azure SQL database.
--   2. If upgrading an existing deployment, the ALTER TABLE
--      blocks below add the new 'type' column safely (idempotent).
--   3. Insert real data using the pattern shown in the sample
--      INSERT statements at the bottom of each section.
--   4. Changes take effect immediately; no application restart
--      is required.
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'portal')
BEGIN
    EXEC('CREATE SCHEMA portal');
END
GO

-- ============================================================
-- TABLE 1: portal.isd_non_support_teams
-- ============================================================
-- ISD users who belong to non-support teams.  Each row pairs
-- one email address with one Azure subscription GUID or AWS
-- account ID.  A user who logs in and is found in this table
-- sees ONLY the IDs on their own row(s).
-- The portal auto-detects the cloud from the ID format:
--   Azure subscription: UUID (e.g. 9ef80a0e-9a68-41d4-9db2-...)
--   AWS account:        12-digit number (e.g. 123456789012)
-- ============================================================

IF NOT EXISTS (
    SELECT 1
    FROM   sys.tables  t
    JOIN   sys.schemas s ON s.schema_id = t.schema_id
    WHERE  s.name = 'portal'
    AND    t.name = 'isd_non_support_teams'
)
BEGIN
    CREATE TABLE portal.isd_non_support_teams (
        id              INT            IDENTITY(1,1) NOT NULL,

        -- Full login email of the ISD non-support-team user.
        email           NVARCHAR(255)  NOT NULL,

        -- Azure subscription GUID *or* AWS account ID assigned to this user.
        -- Azure: UUID format  (e.g. 9ef80a0e-9a68-41d4-9db2-f5579f90af08)
        -- AWS:   12-digit number (e.g. 123456789012)
        subscription_id NVARCHAR(255)  NOT NULL,

        is_active       BIT            NOT NULL CONSTRAINT DF_isd_nst_active   DEFAULT 1,

        created_at_utc  DATETIME2      NOT NULL CONSTRAINT DF_isd_nst_created  DEFAULT SYSUTCDATETIME(),
        updated_at_utc  DATETIME2      NOT NULL CONSTRAINT DF_isd_nst_updated  DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_isd_non_support_teams PRIMARY KEY CLUSTERED (id)
    );

    CREATE UNIQUE NONCLUSTERED INDEX UQ_isd_nst_email_sub
        ON portal.isd_non_support_teams (email, subscription_id);

    CREATE NONCLUSTERED INDEX IX_isd_nst_email
        ON portal.isd_non_support_teams (email);

    PRINT 'Table portal.isd_non_support_teams created successfully.';
END
ELSE
BEGIN
    PRINT 'Table portal.isd_non_support_teams already exists — skipping creation.';
END
GO

-- ----------------------------------------------------------------
-- Sample INSERT for portal.isd_non_support_teams
-- ----------------------------------------------------------------
-- INSERT INTO portal.isd_non_support_teams (email, subscription_id, is_active)
-- VALUES ('nsuser-isd@isd.lacounty.gov', 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff', 1);
-- GO

-- Example (uncomment and replace placeholder values before running):
-- INSERT INTO portal.isd_non_support_teams (email, subscription_id, is_active)
-- SELECT 'nsuser-isd@isd.lacounty.gov', 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff', 1
-- WHERE NOT EXISTS (
--     SELECT 1 FROM portal.isd_non_support_teams
--     WHERE LOWER(email) = 'nsuser-isd@isd.lacounty.gov'
--       AND subscription_id = 'bbbbbbbb-cccc-dddd-eeee-ffffffffffff'
-- );
-- GO


-- ============================================================
-- TABLE 2: portal.isd_linux_windows_team  (type-based access)
-- ============================================================
-- ISD Linux/Windows-team users.  Each row maps an email address
-- to a subscription / account ID and a 'type' group label
-- (e.g. 'wps' = Windows Platform Services,
--        'lps' = Linux Platform Services).
--
-- Access rule:
--   When a user logs in and their email is found here, the
--   portal reads their 'type' value and returns ALL subscription
--   / account IDs in this table that share the same type.  This
--   means every member of the same type group sees the same set
--   of resources — you do not need to list every subscription
--   against every user's email individually.
--
-- Multi-cloud:
--   The subscription_id column holds Azure subscription GUIDs
--   (UUID format) and/or AWS account IDs (12-digit number).
--   The portal filters by cloud format automatically so a single
--   row can be referenced for both Azure and AWS queries.
-- ============================================================

-- ----------------------------------------------------------------
-- Migration: add 'type' column to an existing deployment.
-- This block is safe to run on a freshly-created table too.
-- ----------------------------------------------------------------
IF OBJECT_ID('portal.isd_linux_windows_team', 'U') IS NOT NULL
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM sys.columns
        WHERE  object_id = OBJECT_ID('portal.isd_linux_windows_team')
          AND  name      = 'type'
    )
    BEGIN
        ALTER TABLE portal.isd_linux_windows_team
            ADD type NVARCHAR(50) NULL;
        PRINT 'Column type added to portal.isd_linux_windows_team.';
    END
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM   sys.tables  t
    JOIN   sys.schemas s ON s.schema_id = t.schema_id
    WHERE  s.name = 'portal'
    AND    t.name = 'isd_linux_windows_team'
)
BEGIN
    CREATE TABLE portal.isd_linux_windows_team (
        id              INT            IDENTITY(1,1) NOT NULL,

        -- Full login email of the Linux/Windows-team user.
        email           NVARCHAR(255)  NOT NULL,

        -- Azure subscription GUID *or* AWS account ID.
        -- Azure: UUID format  (e.g. 9ef80a0e-9a68-41d4-9db2-f5579f90af08)
        -- AWS:   12-digit number (e.g. 123456789012)
        subscription_id NVARCHAR(255)  NOT NULL,

        -- Access-group label. All users whose email maps to the same
        -- type see every subscription_id in the table with that type.
        -- Common values: 'wps' (Windows Platform Services),
        --                'lps' (Linux Platform Services).
        type            NVARCHAR(50)   NULL,

        is_active       BIT            NOT NULL CONSTRAINT DF_isd_lwt_active   DEFAULT 1,

        created_at_utc  DATETIME2      NOT NULL CONSTRAINT DF_isd_lwt_created  DEFAULT SYSUTCDATETIME(),
        updated_at_utc  DATETIME2      NOT NULL CONSTRAINT DF_isd_lwt_updated  DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_isd_linux_windows_team PRIMARY KEY CLUSTERED (id)
    );

    CREATE UNIQUE NONCLUSTERED INDEX UQ_isd_lwt_email_sub
        ON portal.isd_linux_windows_team (email, subscription_id);

    CREATE NONCLUSTERED INDEX IX_isd_lwt_email
        ON portal.isd_linux_windows_team (email);

    CREATE NONCLUSTERED INDEX IX_isd_lwt_type
        ON portal.isd_linux_windows_team (type);

    PRINT 'Table portal.isd_linux_windows_team created successfully.';
END
ELSE
BEGIN
    PRINT 'Table portal.isd_linux_windows_team already exists — skipping creation.';
END
GO

-- ----------------------------------------------------------------
-- Sample INSERTs for portal.isd_linux_windows_team
--
-- Key point: you only need ONE row per (email, type) combination
-- to register a user's type group.  The subscription_id on that
-- row can be anything valid; the portal ignores per-user rows
-- and instead returns ALL active rows whose 'type' matches the
-- user's type.  Subscription / account IDs are the rows you add
-- for the TYPE group itself — not per-user.
--
-- Typical pattern:
--   1. Add a row for each (subscription_id / aws_account_id, type).
--   2. Add a row for each (email, type) to register the user.
--      You can reuse any existing subscription_id on the registration
--      row, or create a dedicated "placeholder" row.
-- ----------------------------------------------------------------

-- Register a user as type 'wps' (Windows Platform Services):
-- INSERT INTO portal.isd_linux_windows_team (email, subscription_id, type, is_active)
-- VALUES ('wpsuser@isd.lacounty.gov', 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb', 'wps', 1);
-- GO

-- Add an Azure subscription to the 'wps' group:
-- INSERT INTO portal.isd_linux_windows_team (email, subscription_id, type, is_active)
-- VALUES ('group-entry@isd.lacounty.gov', 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb', 'wps', 1);
-- GO

-- Add an AWS account to the 'lps' group:
-- INSERT INTO portal.isd_linux_windows_team (email, subscription_id, type, is_active)
-- VALUES ('group-entry@isd.lacounty.gov', '123456789012', 'lps', 1);
-- GO

-- Idempotent insert example (uncomment and replace values before running):
-- INSERT INTO portal.isd_linux_windows_team (email, subscription_id, type, is_active)
-- SELECT 'wpsuser@isd.lacounty.gov', 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb', 'wps', 1
-- WHERE NOT EXISTS (
--     SELECT 1 FROM portal.isd_linux_windows_team
--     WHERE LOWER(email) = 'wpsuser@isd.lacounty.gov'
--       AND subscription_id = 'aaaaaaaa-1111-2222-3333-bbbbbbbbbbbb'
-- );
-- GO

PRINT 'ISD subscription tables created/verified successfully.';
GO
