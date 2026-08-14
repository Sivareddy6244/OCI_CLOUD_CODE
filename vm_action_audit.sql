-- ============================================================
-- FILE: vm_action_audit.sql
-- Purpose: Create portal.vm_action_audit — audit log for all
--          destructive and significant VM actions performed via
--          the portal across all three cloud providers (Azure,
--          AWS, GCP).
--
-- Every delete, clone, snapshot, and disk action performed
-- through the "Existing VMs" tab is written to this table so
-- administrators can answer:
--   - Who deleted / cloned / snapshotted a VM?
--   - When did it happen?
--   - Which resource was affected?
--   - Did the action succeed or fail?
--
-- Usage:
--   1. Run this script once against your Azure SQL database.
--   2. The application writes rows automatically on every action.
--   3. No application restart is required after creation.
--   4. This script is idempotent — safe to run multiple times.
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'portal')
BEGIN
    EXEC('CREATE SCHEMA portal');
END
GO

-- ----------------------------------------------------------------
-- Create table
-- ----------------------------------------------------------------
IF NOT EXISTS (
    SELECT 1
    FROM   sys.tables  t
    JOIN   sys.schemas s ON s.schema_id = t.schema_id
    WHERE  s.name = 'portal'
    AND    t.name = 'vm_action_audit'
)
BEGIN
    CREATE TABLE portal.vm_action_audit (
        -- Surrogate primary key
        id                      BIGINT         IDENTITY(1,1) NOT NULL,

        -- ── What happened ────────────────────────────────────
        -- Action type, e.g.:
        --   delete_vm | delete_disk | delete_snapshot |
        --   clone_vm  | snapshot_vm | delete_volume
        action_type             NVARCHAR(64)   NOT NULL,

        -- Cloud provider: azure | aws | gcp
        cloud_provider          NVARCHAR(16)   NOT NULL,

        -- ── Which resource ───────────────────────────────────
        -- Human-readable name of the primary resource
        -- (VM name, snapshot name, disk name, etc.)
        resource_name           NVARCHAR(255)  NULL,

        -- Cloud-native resource ID or identifier
        -- (Azure VM ID, EC2 instance_id, GCP instance name, etc.)
        resource_id             NVARCHAR(512)  NULL,

        -- Azure subscription ID / AWS account ID / GCP project ID
        account_or_subscription NVARCHAR(255)  NULL,

        -- Azure location, AWS region, or GCP zone
        region_or_zone          NVARCHAR(128)  NULL,

        -- Additional context — e.g. Azure resource group,
        -- GCP project, list of also-deleted disks/NICs
        detail                  NVARCHAR(2048) NULL,

        -- ── Who did it ───────────────────────────────────────
        -- Logged-in user's email address (case-insensitive)
        performed_by_email      NVARCHAR(255)  NULL,

        -- Azure AD / Entra ID object ID (oid claim) if available
        performed_by_oid        NVARCHAR(128)  NULL,

        -- ── Outcome ──────────────────────────────────────────
        -- success | failed
        status                  NVARCHAR(16)   NOT NULL CONSTRAINT DF_audit_status DEFAULT 'success',

        -- Error description when status = 'failed'
        error_message           NVARCHAR(2048) NULL,

        -- ── When ─────────────────────────────────────────────
        performed_at_utc        DATETIME2      NOT NULL CONSTRAINT DF_audit_performed_at DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_vm_action_audit PRIMARY KEY CLUSTERED (id)
    );

    -- Fast lookup by user
    CREATE NONCLUSTERED INDEX IX_audit_email
        ON portal.vm_action_audit (performed_by_email)
        INCLUDE (action_type, cloud_provider, resource_name, performed_at_utc);

    -- Fast lookup by resource
    CREATE NONCLUSTERED INDEX IX_audit_resource_name
        ON portal.vm_action_audit (resource_name)
        INCLUDE (action_type, cloud_provider, performed_by_email, performed_at_utc);

    -- Fast lookup by cloud + action + time
    CREATE NONCLUSTERED INDEX IX_audit_cloud_action_time
        ON portal.vm_action_audit (cloud_provider, action_type, performed_at_utc DESC);

    PRINT 'Table portal.vm_action_audit created successfully.';
END
ELSE
BEGIN
    PRINT 'Table portal.vm_action_audit already exists — skipping creation.';
END
GO

PRINT 'vm_action_audit.sql completed.';
GO
