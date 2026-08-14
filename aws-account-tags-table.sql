-- ============================================================
-- FILE: Create and seed portal.aws_account_tags table
-- ============================================================
-- Purpose : Admin-managed fallback for AWS account-level tags.
--           When all four automatic AWS API methods fail to find
--           the AccountNumber tag (e.g., the account has no tagged
--           resources), the portal reads the value from this table.
--
-- Columns:
--   account_id     - AWS account ID (12-digit string, e.g. '792294445508')
--   account_number - Billing account number (e.g. 'P1355422005')
--   account_name   - Optional friendly name for the AWS account
--   is_active      - 1 = use this mapping, 0 = disabled
--
-- How to use:
--   1. Run this script once against the Azure SQL database (portal schema).
--   2. For each AWS account that is missing the AccountNumber tag, INSERT
--      a row with the account_id and account_number.
--   3. No code deployment is needed — the portal reads this at request time.
--
-- Example:
--   INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
--   VALUES ('792294445508', 'P1355422005', 'My AWS Account');
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
    AND    t.name = 'aws_account_tags'
)
BEGIN
    CREATE TABLE portal.aws_account_tags (
        id             INT            IDENTITY(1,1) NOT NULL,
        account_id     NVARCHAR(32)   NOT NULL,
        account_number NVARCHAR(64)   NOT NULL,
        account_name   NVARCHAR(256)  NULL,
        is_active      BIT            NOT NULL CONSTRAINT DF_aws_account_tags_is_active DEFAULT 1,
        created_at_utc DATETIME2      NOT NULL CONSTRAINT DF_aws_account_tags_created   DEFAULT SYSUTCDATETIME(),
        updated_at_utc DATETIME2      NOT NULL CONSTRAINT DF_aws_account_tags_updated   DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_aws_account_tags        PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_aws_account_tags_acctid UNIQUE (account_id),
        CONSTRAINT CK_aws_account_tags_id     CHECK (LEN(LTRIM(RTRIM(account_id))) > 0)
    );
END
GO

-- ── Seed account mappings from the AWS billing spreadsheet ─────────────────────
-- Seed data from excel/AWS Billing Account Numbers list.xlsx (generated mapping by account name).
-- Uses idempotent inserts keyed by account_id.
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '005595088033', 'A1915026054', 'Coroner'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '005595088033');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '011528284338', 'A1001025002', 'AWS-AAB_CONNECT-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '011528284338');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '013611718990', 'A1520014592', 'Public Defender IT Agency'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '013611718990');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '013637809067', 'A2590102900', 'DPSS-AWS-Connect'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '013637809067');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '014085571870', 'A2791014032', 'DEO AWS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '014085571870');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '017820666232', 'A1001025002', 'AWS-AAB_CONNECT-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '017820666232');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '017820666235', 'A1001025002', 'AWS-AAB_CONNECT-TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '017820666235');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '021335304183', 'P1319591233', 'ITSS AppStream'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '021335304183');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '023800203545', 'P1333891081', 'ISD IDD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '023800203545');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '025217829020', 'P1317690040', 'ISD Telecom'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '025217829020');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '030708491905', 'A3347497651', 'Public Health - Pinpoint'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '030708491905');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '058264242063', 'A1020024019', 'AWS-ASESSOR_DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '058264242063');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '059659026606', 'A6150039412', 'DHS_AWS_Enterprise'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '059659026606');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '060127551817', 'P1343091230', 'ENTERPRISE SECURITY'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '060127551817');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '061039762682', 'A1070018468', 'AWS-AUDITOR_CONNECT-TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '061039762682');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '061499950385', 'A2781023048', 'magostinelliWDACS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '061499950385');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '062006678460', 'A1130043035', 'RRCC-AWS-S3'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '062006678460');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '069872218693', 'A2679200110', 'DCFS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '069872218693');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '077973199198', 'A1403014632', 'District_Attorney-AWS_Connect'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '077973199198');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '081468143510', 'A1500002025', 'LACJCOD_SUB_AWS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '081468143510');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '137068222216', 'P1355791272', 'AWS-TDEIS-TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '137068222216');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '149536492733', 'A1010024036', 'AWS-ECRC_CONNECT-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '149536492733');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '150197995471', 'A1130097017', 'RRCC-ACGR'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '150197995471');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '168395994234', 'P1312710801', 'ISD GGSD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '168395994234');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '192752785889', 'P1355791272', 'LAISD - Backup Storage'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '192752785889');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '196049140327', 'P1343091230', 'ISD Secure Access Engineering'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '196049140327');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '211125782991', 'P1355422005', 'lac-abc-primary'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '211125782991');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '221082194031', 'A4042825001', 'AWS-FIRE-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '221082194031');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '221082201026', 'A1070018468', 'AWS-AUDITOR_CONNECT-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '221082201026');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '228656903909', 'A1130092272', 'AWS-RRCC_VSD_SANDBOX'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '228656903909');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '242013862987', 'P1355891200', 'ISD Openshift'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '242013862987');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '245805261858', 'P1343091233', 'AWS-DMZ-Web-test-1'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '245805261858');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '280928810037', 'A4790000012', 'AWS Connect - CleanLA'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '280928810037');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '283661260993', 'A1520014592', 'PUBLIC DEFENDER'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '283661260993');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '318500746392', 'A5579539320', 'LACERA'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '318500746392');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '321391860655', 'P1344991232', 'CED-ESE'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '321391860655');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '328705060255', 'A1130092315', 'RRCC - LAVOTE ELECTION RESULTS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '328705060255');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '330217625594', 'A1009122400', 'ISAB'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '330217625594');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '332070355516', 'P1344991232', 'Audit'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '332070355516');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '339712831907', 'A1095080018', 'AWS-TREASURY_TAX_CONNECT-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '339712831907');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '339713154018', 'A1020024019', 'AWS-ASESSOR_TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '339713154018');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '340752794809', 'A1095087051', 'AWS-TREASURY_TAX'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '340752794809');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '347363593519', 'P1343091233', 'AWS-SECURITY_PaloAltoPROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '347363593519');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '351451326486', 'P1333700003', 'eGIS_ArcGIS_Enterprise'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '351451326486');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '353922334669', 'A2679200296', 'AWS-DCFS-Oracle'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '353922334669');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '365643788452', 'P1319591233', 'LACountyISD_Workspaces'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '365643788452');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '398284229904', 'P1333891081', 'IDD Websites'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '398284229904');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '404142233', 'A1873000268', 'IDD GIS Caltrap'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '404142233');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '000404142233', 'A1873000268', 'IDD GIS Caltrap'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '000404142233');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '412116382044', 'P1343091233', 'AWS-SECURITY_PaloAltoPOC'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '412116382044');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '428780238092', 'A5579539320', 'LACERA_Dev'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '428780238092');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '429686675059', 'P1343091233', 'SharedServices'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '429686675059');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '443914036196', 'A1020024019', 'Assessor'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '443914036196');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '451808593858', 'P1333891081', 'ISD IDD Managed'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '451808593858');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '472110193540', 'A2590191100', 'DPSS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '472110193540');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '476553995083', 'P1355491964', 'ISD-SSB-CSI'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '476553995083');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '487836127787', 'A2590192900', 'DPSS ITD Network Management'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '487836127787');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '487954424959', 'P1333700003', 'GIS_Cloud_Platform'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '487954424959');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '509807155577', 'A1403014632', 'District Attorney'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '509807155577');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '514044800693', 'P1343091232', 'Log archive'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '514044800693');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '526648353896', 'A2590191100', 'County of Los Angeles, DPSS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '526648353896');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '527399475385', 'A6150039412', 'DHS_Private_5G_Dev'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '527399475385');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '533266964199', 'A1020024019', 'AWS-ASESSOR_PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '533266964199');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '534978226835', 'P1333700003', 'SSB-EGIS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '534978226835');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '536874876417', 'A8362000001', 'LACounty Diversion'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '536874876417');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '549344408264', 'P1356101230', 'ISD MCD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '549344408264');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '559265186679', 'A5730000015', 'PUBLIC WORKS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '559265186679');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '562401457670', 'A2000007161', 'DHS-VMC'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '562401457670');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '589636153376', 'A1020021203', 'AWS-ASESSOR_Veeam'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '589636153376');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '590075511264', 'P1343091233', 'ENTERPRISE NETWORKING'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '590075511264');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '598041321384', 'P1312710801', 'ISD-CAB'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '598041321384');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '600198011871', 'P1355422005', 'ISD TD eCloud'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '600198011871');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '607104513569', 'A4042825001', 'AWS-FIRE-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '607104513569');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '617973292335', 'A5710000105', 'AWS-DPW-PROJECT_SANDBOX'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '617973292335');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '619375803757', 'P1355491230', 'DLT LA County'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '619375803757');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '621476030081', 'P1355891200', 'CaaS ECM EKS Project'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '621476030081');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '632732354594', 'A1130092315', 'RRCC - AWS Connect Elections'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '632732354594');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '637423425224', 'A1130092315', 'AWS-RRCC_DW_ELECTION-POC'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '637423425224');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '653674545758', 'A1120151808', 'Human Resources'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '653674545758');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '654654420792', 'A1520014592', 'AWS-PUBLIC_DEFENDER_CONNECT-TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '654654420792');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '682625837619', 'A2650063215', 'Military_and_Veterans_Affairs'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '682625837619');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '686255971863', 'P1344991232', 'AWS-ISD-CGO_CSA_IR'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '686255971863');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '693718126367', 'P1319591233', 'ITSS_Share'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '693718126367');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '726203495796', 'P1355991201', 'Mainframe_VTS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '726203495796');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '728394805904', 'A5710000099', 'AWS-PW_DISPATCH_CONNECT'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '728394805904');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '730335175640', 'A1520014592', 'AWS-PUBLIC_DEFENDER_CONNECT-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '730335175640');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '730335308135', 'A1095080018', 'AWS-TREASURY_TAX_CONNECT-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '730335308135');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '742156547861', 'A1130092315', 'RRCC_DEV_TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '742156547861');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '743309932854', 'A3347497651', 'Public Health'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '743309932854');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '743524583132', 'P1312710801', 'ISD-GGSD-ISDHR'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '743524583132');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '750294788650', 'A1710072008', 'Probation'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '750294788650');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '754405460525', 'P1355791272', 'ENTERPRISE INFRASTRUCTURE'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '754405460525');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '761763126862', 'P1333591230', 'AWS CONNECT'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '761763126862');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '762576794010', 'A1130097017', 'RRCC - AWS Connect'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '762576794010');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '783764586537', 'P1355891200', 'AWS-TD_OSS_LPS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '783764586537');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '789082305884', 'P1355491964', 'PUBLIC INFRASTRUCTURE SERVICES'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '789082305884');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '792294445508', 'A1895001511', 'Animal Care'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '792294445508');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '820242947574', 'A1010024036', 'AWS-ECRC_CONNECT-PROD'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '820242947574');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '851725198835', 'A1095080018', 'AWS-TREASURY_TAX_CONNECT-TEST'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '851725198835');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '872017552827', 'A2679200112', 'DCFS Dev'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '872017552827');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '875510801412', 'P1343091233', 'PUBLIC SERVICES POC'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '875510801412');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '888577053709', 'A1070018468', 'AWS-AUDITOR_CONNECT-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '888577053709');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '897768183437', 'A1130092272', 'AWS-RRCC_ADMIN_SANDBOX'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '897768183437');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '905418230151', 'A1520014592', 'AWS-PUBLIC_DEFENDER_CONNECT-DEV'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '905418230151');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '905418462075', 'P1355891200', 'AWS-CaaS_Rancher_Production'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '905418462075');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '906514578947', 'A1935039360', 'Planning'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '906514578947');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '914286927211', 'P1355491964', 'ENTERPRISE AUDITING'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '914286927211');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '919672611458', 'A1557524007', 'APD-AWS1'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '919672611458');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '932757390505', 'P1317593182', 'AWS-IRSD_BeOn'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '932757390505');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '942917258976', 'P1355891200', 'CaaS-Rancher-Non-prod'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '942917258976');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '960881837580', 'A4120000464', 'AWS-PubLib-MediaArchive'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '960881837580');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '964116004563', 'A4120000464', 'Library'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '964116004563');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '971334862800', 'P1343091233', 'AWS-PaloAlto-Ingress'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '971334862800');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '992382632216', 'P1355491234', 'AWS-Monitoring'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '992382632216');
INSERT INTO portal.aws_account_tags (account_id, account_number, account_name)
SELECT '992557151693', 'P1333791200', 'SSB EGIS CAMS'
WHERE NOT EXISTS (SELECT 1 FROM portal.aws_account_tags WHERE account_id = '992557151693');

-- Unmatched Excel rows (not inserted because no matching account_name was found in ALLOWED_AWS_ACCOUNTS):
-- A2140051203 | Consumer and Business Affairs
-- A1009122400 | LACounty-ISAB - cjistables
-- P1343091233 | AWS-PaloAlto-DMZ
-- A1130092315 | RRCC Hoth - Production
-- A1009122400 | Subpoena
-- P1355422005 |  AWS-eCloud_Services
-- A1369023005 | AWS-CIO-DEV
GO
