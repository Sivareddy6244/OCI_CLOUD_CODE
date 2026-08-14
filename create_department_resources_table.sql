-- ============================================================
-- FILE 1: Create portal.portal_department_resources table
-- ============================================================
-- Purpose : Pre-loaded reference table maintained by administrators.
--           Maps Azure subscriptions / AWS accounts to the department
--           name extracted from each user's login email.
--
-- Email format : <user>@<department>.lacounty.gov
-- Examples     : ADahbashi@dhs.lacounty.gov     -> dept = 'dhs'
--                CLANZA@auditor.lacounty.gov    -> dept = 'auditor'
--                JHatami@ceo.lacounty.gov       -> dept = 'ceo'
--
-- When a user logs in, the backend extracts the department from
-- their email, queries this table (WHERE status = 'Active'), and
-- automatically shows them only the subscriptions / accounts that
-- belong to their department — no manual registration required.
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'portal')
BEGIN
    EXEC('CREATE SCHEMA portal');
END
GO

IF NOT EXISTS (
    SELECT 1
    FROM   sys.tables  t
    JOIN   sys.schemas s ON s.schema_id = t.schema_id
    WHERE  s.name = 'portal'
    AND    t.name = 'portal_department_resources'
)
BEGIN
    CREATE TABLE portal.portal_department_resources (
        id                INT            IDENTITY(1,1) NOT NULL,

        -- Human-readable subscription / account name
        subscription_name NVARCHAR(255)  NOT NULL,

        -- Azure subscription GUID   (e.g. 9ef80a0e-9a68-41d4-9db2-f5579f90af08)
        -- AWS account ID (12 digits) (e.g. 100035083132)
        -- NULL is allowed here so rows can be inserted before the ID is known;
        -- the unique index below applies only to non-NULL values.
        subscription_id   NVARCHAR(255)  NULL,

        -- 'Active' | 'Inactive'
        status            NVARCHAR(50)   NOT NULL CONSTRAINT DF_dept_res_status  DEFAULT 'Active',

        -- Department key derived from email domain (always lower-case)
        -- e.g. 'dhs', 'auditor', 'ceo', 'isd'
        department        NVARCHAR(255)  NOT NULL,

        -- 'azure' or 'aws'
        cloud             NVARCHAR(50)   NOT NULL CONSTRAINT DF_dept_res_cloud   DEFAULT 'azure',

        -- Optional: a representative email from that department (for reference)
        sample_mail       NVARCHAR(255)  NULL,

        created_at_utc    DATETIME2      NOT NULL CONSTRAINT DF_dept_res_created DEFAULT SYSUTCDATETIME(),
        updated_at_utc    DATETIME2      NOT NULL CONSTRAINT DF_dept_res_updated DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_portal_department_resources PRIMARY KEY CLUSTERED (id)
    );

    -- Prevent duplicate (department, cloud, subscription_id) — NULL subscription_ids
    -- are excluded from this index and can appear multiple times.
    CREATE UNIQUE NONCLUSTERED INDEX UQ_dept_res_dept_cloud_sub
        ON portal.portal_department_resources (department, cloud, subscription_id)
        WHERE subscription_id IS NOT NULL;

    -- Speed up department look-ups (the primary query pattern)
    CREATE NONCLUSTERED INDEX IX_dept_res_department
        ON portal.portal_department_resources (department);

    PRINT 'Table portal.portal_department_resources created successfully.';
END
ELSE
BEGIN
    -- Migration guard: add subscription_id NULLability if column is NOT NULL
    -- (only needed when upgrading from an earlier schema version)
    PRINT 'Table portal.portal_department_resources already exists — no changes made.';
END
GO
