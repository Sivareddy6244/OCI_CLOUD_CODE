-- ============================================================
-- FILE: admins-table.sql
-- Purpose: Create and seed the portal.portal_admins table.
--
-- This table stores the email addresses of portal administrators.
-- When a user logs in, the backend checks this table (and falls
-- back to the hardcoded ADMIN_EMAILS list when the DB is
-- unavailable).  Admins see ALL AWS accounts and ALL Azure
-- subscriptions regardless of their department.
--
-- Usage:
--   1. Run this script against your Azure SQL database.
--   2. Add / remove admin emails via INSERT / DELETE as needed.
--   3. The application reads this table at login time; no restart
--      is required when the table contents change.
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
    AND    t.name = 'portal_admins'
)
BEGIN
    CREATE TABLE portal.portal_admins (
        id             INT            IDENTITY(1,1) NOT NULL,

        -- Full login email of the admin (case-insensitive comparison is used
        -- in queries, but store the canonical mixed-case form here for display).
        email          NVARCHAR(255)  NOT NULL,

        -- Human-readable note: who this person is / why they have admin access.
        display_name   NVARCHAR(255)  NULL,

        -- 'Active' | 'Inactive'  — set to 'Inactive' to revoke without deleting.
        status         NVARCHAR(50)   NOT NULL CONSTRAINT DF_admins_status  DEFAULT 'Active'
                                               CONSTRAINT CK_admins_status  CHECK (status IN ('Active', 'Inactive')),

        created_at_utc DATETIME2      NOT NULL CONSTRAINT DF_admins_created DEFAULT SYSUTCDATETIME(),
        updated_at_utc DATETIME2      NOT NULL CONSTRAINT DF_admins_updated DEFAULT SYSUTCDATETIME(),

        CONSTRAINT PK_portal_admins PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_portal_admins_email UNIQUE (email)
    );

    -- Speed up the per-login look-up (WHERE LOWER(email) = LOWER(?))
    CREATE NONCLUSTERED INDEX IX_portal_admins_email
        ON portal.portal_admins (email);

    PRINT 'Table portal.portal_admins created successfully.';
END
ELSE
BEGIN
    PRINT 'Table portal.portal_admins already exists — skipping creation.';
END
GO

-- ----------------------------------------------------------------
-- Seed admin emails
-- Replace / extend this list with actual admin email addresses.
-- ----------------------------------------------------------------
MERGE portal.portal_admins AS target
USING (VALUES
    ('EFlores@isd.lacounty.gov',                    'E. Flores'),
    ('MSalihue@isd.lacounty.gov',                   'M. Salihue'),
    ('SAttoti@isd.lacounty.gov',                    'S. Attoti'),
    ('BChacko@isd.lacounty.gov',                    'B. Chacko'),
    ('yjin@isd.lacounty.gov',                       'Y. Jin'),
    ('aalmuhajab@isd.lacounty.gov',                 'A. Almuhajab'),
    ('anavarro.consultant@isd.lacounty.gov',        'A. Navarro (Consultant)'),
    ('jyang@isd.lacounty.gov',                      'J. Yang'),
    ('jcanchola@isd.lacounty.gov',                  'J. Canchola'),
    ('kzhang2@isd.lacounty.gov',                    'K. Zhang'),
    ('klake@isd.lacounty.gov',                      'K. Lake'),
    ('nnguyen@isd.lacounty.gov',                    'N. Nguyen'),
    ('raryal@isd.lacounty.gov',                     'R. Aryal'),
    ('ragi.consultant@isd.lacounty.gov',            'R. Agi (Consultant)'),
    ('umohammed.consultant@isd.lacounty.gov',       'U. Mohammed (Consultant)'),
    ('ebarbosadasilva.consultant@isd.lacounty.gov', 'E. Barbosa Da Silva (Consultant)'),
    ('epetrosy@isd.lacounty.gov',                   'E. Petrosy'),
    ('hnguyen2@isd.lacounty.gov',                   'H. Nguyen'),
    ('tlee2@isd.lacounty.gov',                      'T. Lee'),
    ('uvydyula@isd.lacounty.gov',                   'U. Vydyula'),
    ('hche@isd.lacounty.gov',                       'H. Che'),
    ('tpoon@isd.lacounty.gov',                      'T. Poon'),
    ('esangalang@isd.lacounty.gov',                 'E. Sangalang'),
    ('vle@isd.lacounty.gov',                        'V. Le'),
    ('aoyewumi.consultant@isd.lacounty.gov',        'A. Oyewumi (Consultant)'),
    ('hwong@isd.lacounty.gov',                      'H. Wong'),
    ('rkolmi@isd.lacounty.gov',                     'R. Kolmi'),
    ('ctum@isd.lacounty.gov',                       'C. Tum'),
    ('dgan@isd.lacounty.gov',                       'D. Gan'),
    ('elopez3@isd.lacounty.gov',                    'E. Lopez'),
    ('rabrahamian.consultant@isd.lacounty.gov',     'R. Abrahamian (Consultant)'),
    ('rkwong2@isd.lacounty.gov',                    'R. Kwong'),
    ('schauhan@isd.lacounty.gov',                   'S. Chauhan'),
    ('sshiri@isd.lacounty.gov',                     'S. Shiri'),
    ('smihlar@isd.lacounty.gov',                    'S. Mihlar'),
    ('sbuickians@isd.lacounty.gov',                 'S. Buickians'),
    ('wli@isd.lacounty.gov',                        'W. Li'),
    ('tchen2@isd.lacounty.gov',                     'T. Chen'),
    ('cwilliamsjr@isd.lacounty.gov',                'C. Williams Jr'),
    ('dsargsyan2@isd.lacounty.gov',                 'D. Sargsyan'),
    ('fchang@isd.lacounty.gov',                     'F. Chang'),
    ('gyiu@isd.lacounty.gov',                       'G. Yiu'),
    ('jsuzara@isd.lacounty.gov',                    'J. Suzara'),
    ('ktou@isd.lacounty.gov',                       'K. Tou'),
    ('mperez2@isd.lacounty.gov',                    'M. Perez'),
    ('nchea@isd.lacounty.gov',                      'N. Chea'),
    ('phuon@isd.lacounty.gov',                      'P. Huon'),
    ('rparker@isd.lacounty.gov',                    'R. Parker'),
    ('axu@isd.lacounty.gov',                        'A. Xu'),
    ('acheng@isd.lacounty.gov',                     'A. Cheng'),
    ('dsuh@isd.lacounty.gov',                       'D. Suh'),
    ('halmuhajab@isd.lacounty.gov',                 'H. Almuhajab'),
    ('fpuyatjr@isd.lacounty.gov',                   'F. Puyat Jr'),
    ('jaguiling@isd.lacounty.gov',                  'J. Aguiling'),
    ('msudarshanam@isd.lacounty.gov',               'M. Sudarshanam'),
    ('mdelarosa@isd.lacounty.gov',                  'M. De La Rosa'),
    ('cchang@isd.lacounty.gov',                     'C. Chang'),
    ('sperez3@isd.lacounty.gov',                    'S. Perez'),
    ('achung@isd.lacounty.gov',                     'A. Chung'),
    ('mgonzalez2@isd.lacounty.gov',                 'M. Gonzalez')
) AS source (email, display_name)
ON LOWER(target.email) = LOWER(source.email)
WHEN NOT MATCHED BY TARGET THEN
    INSERT (email, display_name, status)
    VALUES (source.email, source.display_name, 'Active');
GO

PRINT 'portal.portal_admins seeded successfully.';
GO
