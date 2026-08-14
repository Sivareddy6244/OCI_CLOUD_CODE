-- ============================================================
-- FILE: deployment-status-table.sql
-- Purpose: Create the portal.deployment_status table used to
--          persist VM deployment status across server restarts.
--
-- The backend writes a row for every deployment attempt and
-- reads it back as a fallback when the in-memory TTLCache has
-- been cleared (e.g. after an Azure App Service restart).
--
-- Usage:
--   1. Run this script against your Azure SQL database once.
--   2. No application restart is required after creation.
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
    AND    t.name = 'deployment_status'
)
BEGIN
    CREATE TABLE portal.deployment_status (
        -- Deployment identifier returned to the frontend (e.g. "ecloudtest-013d315a8745")
        deployment_id  NVARCHAR(128)  NOT NULL,

        -- Latest known state: starting | preparing | creating_nic | resolving_image |
        --                     creating_vm | completed | failed
        status         NVARCHAR(64)   NOT NULL,

        -- Human-readable progress message
        message        NVARCHAR(512)  NULL,

        -- Azure resource ID of the created VM (populated on completion)
        vm_id          NVARCHAR(512)  NULL,

        -- Error detail (populated on failure)
        error          NVARCHAR(1024) NULL,

        -- When this row was last written
        updated_at_utc DATETIME2      NOT NULL CONSTRAINT DF_deployment_status_updated DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_deployment_status PRIMARY KEY CLUSTERED (deployment_id)
    );

    PRINT 'Table portal.deployment_status created successfully.';
END
ELSE
BEGIN
    PRINT 'Table portal.deployment_status already exists — skipping creation.';
END
GO
