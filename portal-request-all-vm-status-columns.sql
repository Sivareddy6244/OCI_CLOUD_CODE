-- ============================================================
-- FILE: portal-request-all-vm-status-columns.sql
-- Purpose: Add VM deployment outcome columns to portal.portal_request_all
-- ============================================================

IF NOT EXISTS (SELECT 1 FROM sys.schemas WHERE name = 'portal')
BEGIN
    EXEC('CREATE SCHEMA portal');
END
GO

IF OBJECT_ID('portal.portal_request_all', 'U') IS NULL
BEGIN
    PRINT 'Table portal.portal_request_all not found. Create it first, then re-run this script.';
    RETURN;
END
GO

IF COL_LENGTH('portal.portal_request_all', 'vm_deployment_status') IS NULL
BEGIN
    ALTER TABLE portal.portal_request_all
    ADD vm_deployment_status NVARCHAR(64) NULL;
    PRINT 'Added column portal.portal_request_all.vm_deployment_status';
END
ELSE
BEGIN
    PRINT 'Column portal.portal_request_all.vm_deployment_status already exists.';
END
GO

IF COL_LENGTH('portal.portal_request_all', 'vm_error_logs') IS NULL
BEGIN
    ALTER TABLE portal.portal_request_all
    ADD vm_error_logs NVARCHAR(MAX) NULL;
    PRINT 'Added column portal.portal_request_all.vm_error_logs';
END
ELSE
BEGIN
    PRINT 'Column portal.portal_request_all.vm_error_logs already exists.';
END
GO
