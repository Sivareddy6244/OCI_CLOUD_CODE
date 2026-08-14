-- ============================================================
-- FILE 2: Sample INSERT statements for portal.portal_department_resources
-- ============================================================
-- Source data:
--   Azure : "Azure Subscriptions list.xlsx" (249 rows with subscription IDs)
--   AWS   : "aws accounts list.xlsx"
--             - 12 rows include the account ID (embedded in the spreadsheet)
--             - 123 rows list account names only; subscription_id = NULL
--               (to be populated by an administrator once IDs are confirmed)
--
-- Run this script AFTER create_department_resources_table.sql.
-- ============================================================

SET NOCOUNT ON;
GO

-- ── AZURE SUBSCRIPTIONS ───────────────────────────────────────────────────────
PRINT 'Inserting Azure subscriptions...';
GO

INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-Auditor_PropTax', '9ef80a0e-9a68-41d4-9db2-f5579f90af08', 'Active', 'auditor', 'azure', 'CLANZA@auditor.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-CEO-ECRC_IMS_Infohub_Integration', '96b7c79f-cb34-4c8d-a96d-35408a7fc7d7', 'Active', 'ceo', 'azure', 'JHatami@ceo.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-DHS-ENT-DataAnalytics', '7947bd16-7686-46e7-9906-eaea6254de21', 'Active', 'dhs', 'azure', 'ADahbashi@dhs.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS SQL Dev/Test', '84a6d583-b328-4e00-99be-690cdfe6947e', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS-CopilotAIAgentsTest', 'aa712ac5-a8ba-408f-8d8c-d6d83eaab5fc', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Department of Health Services', 'fea7c3a0-3fc5-4a77-85bf-18ed49c48f3a', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS-SQL-DEV', '6acff732-b6a5-4511-bf50-b915f20f256b', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-DMH-Security', '0845818e-d3ef-4a28-a983-f758d14a3be4', 'Active', 'dmh', 'azure', 'DYang@dmh.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-YOUTH_DEVELOPMENT', '6082c928-7b46-4e97-9d7b-d4cc40c4ae1f', 'Active', 'dyd', 'azure', 'HWeisberg@dyd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-PubLibrary-Cameyo', '6922f3ed-cc2f-43b6-a1b6-4bbc65b9ce1e', 'Active', 'library', 'azure', 'WByon@library.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ProbArcPOC', '22533538-cb37-4fcb-a365-719636de430c', 'Active', 'probation', 'azure', 'Nhan.Nguyen@probation.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-PUBDEF_IDCO-General', '3e479d09-0bed-4832-b276-ccc8d7c3e6bc', 'Active', 'pubdef', 'azure', 'e678892PIMPD@pubdef.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-RRCC_LAC-EMS-STAGE3', 'ebf67848-1336-4c8c-9ded-ffff4f87f1b7', 'Active', 'rrcc', 'azure', 'AGuedea@rrcc.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-RRCC_LAC-EMS-STAGE', '2793b24b-934f-43d8-b2d4-4bbb3fdffb57', 'Active', 'rrcc', 'azure', 'AGuedea@rrcc.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-RRCC_LAC-EMS-PROD', '6b483af8-ff05-49c1-b480-196659b1a50e', 'Active', 'rrcc', 'azure', 'AGuedea@rrcc.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-GGSD_Data-Engineering', '1f271952-b0a1-498e-bfae-97fbb48af978', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-SecApps', '74f90525-841c-4df6-bd42-498542aa8d55', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CGO-CED-AppSec', 'b31c15f9-dd1f-4a84-87b1-6969e05f3a15', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-SECURITY_PaloAltoPOC', '5cba84c4-7126-448e-8a76-0ba4b603deea', 'Active', 'isd', 'azure', 'check this');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ITSS-O365', 'd92d1639-21d5-4698-a480-668c8fea6c75', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ITSS_W365_CPC', 'e0963719-ba4d-40f3-8015-344186206947', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD_Centralized-GenAI-Prod', '9c22b388-0504-44bd-9894-426b25770b64', 'Active', 'isd', 'azure', 'VMilchorena@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD_Centralized-GenAI-Dev', 'fd451e4a-18b6-4d4f-8f6b-afada5e1888f', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LZ-Networking', '79b758da-88f5-4228-9fa0-2ffbe6062dbb', 'Active', 'isd', 'azure', 'e493038PIMISD@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LZ-Identity', '8388bfa8-8bc4-45e6-8917-5211df31664a', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LZ-Management', '8ad9310f-9e39-452b-95fa-5b0436ef584a', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', '6fad4d64-8a98-42d4-9df2-1c5bdd74069d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PUBLIC INFRASTRUCTURE SERVICES', 'f782d41b-e4be-488c-9034-280ab3bad928', 'Active', 'isd', 'azure', 'tdf5 team');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '4343d43c-3196-42e4-a66e-6764a21afa0d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', '9ce4e051-d8ee-4b40-ad07-e65e62769b29', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise - Richard', 'bef2c053-9871-44ba-bbe8-045340839425', 'Active', 'assessor', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '56691876-937c-403f-b94e-92371725ce9d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCCAppDevOps', '42d24cfc-3bb3-42cc-b311-d78915bee495', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-AU-SB', 'bfd6b50a-6da1-4776-a4b2-4fdce6ef3223', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', '2b4a7516-c9e9-4388-8690-9bc1953cb46d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS-SQL-PROD', '09b98150-07a9-494a-8cf0-02656787e9c4', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-CBA', 'dd4a1d63-ee8c-45fe-bbb8-6e9e558b461e', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Sponsorship 2', '2a0d35bb-1132-44cc-90c6-f8027404e58a', 'Active', 'dpss', 'azure', 'AbdulQadir@dpss.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CGO-AD', '2bf029de-12a5-4055-85a2-1c261a323c0d', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-TDOSS-mindlamp', '982fd227-0dbb-4b1d-8a14-4e64e4cd8f67', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-IDD', 'b7441a96-09fb-4e40-bf9e-0ef60ae0ab57', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-GGSD_ISDHR', '8e3652cb-c512-4e43-8ab1-0017d5205dfe', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC Probation', '1f24db2d-fe5b-4042-addb-b09270bac45f', 'Active', 'probation', 'azure', 'Charlie.Chang@probation.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DPSS', 'ecb65b4b-e891-4315-ad84-becb5f2c876e', 'Active', 'dpss', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '3d26f388-d42e-4a6e-92c3-a07e8273c616', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Master Microsoft Azure Enterprise', 'eb747789-703b-49bc-a731-f6012c7fbd18', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', 'a5f4fb8d-abf5-4560-b0f2-252c4254b54a', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC-PRA', '402d87ea-c783-4c5b-a2bd-73acaceae154', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-GGSD_ENTERPRISE', '8c0c906d-c27a-483a-9b2e-ec5eeed795f2', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-PR', 'f4b9c077-2b11-4951-a3f5-19c38f60432a', 'Active', 'parks', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '74cc40e2-3ee4-4fa5-a529-b8103b7fe57f', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DPH_HIDEX_sub_QA', 'e0cb0d2f-6d86-41a0-80ba-42e38c9eee2d', 'Active', 'ph', 'azure', 'MHussain@ph.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '044589aa-1fad-47d9-af3b-ed2b5d5fcc92', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Library', '406145af-aebf-4ad2-b11e-c8e0c5f0ef30', 'Active', 'dmh', 'azure', 'CChiu@dmh.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Pay-As-You-Go', '25ba0e1c-f4a1-40ad-99f8-1791c9c22212', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-IDD-CollaborationApps', 'fd272e62-021c-4352-8cab-7244e1adbda9', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '928a26aa-283c-4248-b7c5-b47c1799cf4e', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LA-Huemen-ImpactLab-Solutions', 'd0b796d2-8536-4b51-9356-41c8dd549820', 'Active', 'cio', 'azure', 'CPailma@cio.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DPH_HIDEX_sub_Prod', '236d8f94-cf39-40f7-a364-8d0e478e8fbe', 'Active', 'ph', 'azure', 'AGoldenberg@ph.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '4561e3db-11a4-49b8-ae38-68f64875a873', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-DLP-Dashboard', '7552c3ec-1de4-4447-9ae0-df5d936d6691', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-AVD-D640-PROB', '07395b0e-8143-4d81-9ebc-baf71e0ee5e9', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-PaloAlto_Prod', '245e6311-10dc-42b4-afbe-f42bd4ac4856', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional', 'f68b0c27-6a68-4d3b-be72-4c6abca43a80', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-AU', '12752ce4-1105-4b09-b5c8-eb852d12da72', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-AVD-D100-DHR', '39f3953b-a500-49d0-a905-6278aeae0d71', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ProbAzureComD01', '82268951-76a4-46e5-a7f0-853dacb2a4bb', 'Active', 'probation', 'azure', 'Angel.Orduno@probation.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '0702595c-45e8-4f97-9670-b48d4a2f8158', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ProbAzureComProd01', 'd752256b-15f1-48ca-b443-842f0c8f2e3e', 'Active', 'probation', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-MISD', '8dd90177-410d-45ec-bb06-8673a18055dc', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Health', '770cae7b-8fb3-4f88-9161-8de409e2aa3c', 'Active', 'ph', 'azure', 'yufeng@ph.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-GGSD_UIPATH', '30029690-11e5-4610-8a40-0ee1526b3246', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Fire', 'ce76c69b-c2e9-4c22-aa24-0ac430753bb4', 'Active', 'fire', 'azure', 'Cody.Bruce@fire.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-SSB-DevOps', '15f64e9b-30b5-4600-a567-6c15cbabe6e9', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Library', '21cecf03-42d8-45d4-9427-01ff9920261e', 'Active', 'library', 'azure', 'WByon@library.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CEO', 'f8c1870b-46a7-460c-b833-7ea16523d751', 'Active', 'ceo', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-TD-EIS', '8b5347d3-499e-4d6d-96d9-5343076a83ee', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TD-EIS-PRIMARY-STORAGE', '289db2c3-793c-484f-85dd-b4c5dba94ade', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-EIS-SECONDARY-STORAGE', 'dbf0d4a9-85e3-45a6-8038-6144b3112dbf', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD ITSS', '95b67025-a02c-478f-8fe9-8ab79f3aa423', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '2d09ec2c-cc70-49f7-9e70-7278356e6b4c', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '7ed17c5a-da76-4a6e-b56b-33f038ebfca7', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH PH', '70f33880-5fff-4dd4-b067-99154d1e286a', 'Active', 'ph', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DMH CAz', '6479313d-6987-4601-b375-9dbef6e25516', 'Active', 'dmh', 'azure', 'APereda@dmh.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ACWM', 'a6e505eb-df79-49fd-bf85-8621c8558b5d', 'Active', 'acwm', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ProbAzureComT01', '4b0499fe-f776-49c3-accf-fdeb32c3e658', 'Active', 'probation', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD CAB', 'c36eea68-5ff3-4bac-9272-4ee004bcce3a', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMH_HIDEX_sub_Dev', '3795e2b5-f1fa-4ff6-8205-f58e1e4d0936', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional', 'e18f36be-1ced-4f0e-9909-88ab3371195b', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH_DMBI_SUB_DEVTEST', 'eac74712-289c-49f8-aed0-7eeffff71e17', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Animal Care and Control', 'b72dab7d-e9ab-4f85-9d65-05a78805bdc0', 'Active', 'animalcare', 'azure', 'SQazi@animalcare.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', 'f5f3c77d-846c-43ba-86b8-ba4ecd21650b', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-TD-eCloud', 'ef41a7a7-df63-46b8-83ec-a397b194a107', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH_EntInf_sub_Prod', '57babbed-0a90-47f0-b1bd-c9d90cee36ce', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', '0f29caf3-431c-449b-b1b9-009504c3abe6', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('WCD GenAI', '1b34d28d-3ccb-4a73-8093-c9bb048473ab', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-OMPI-DELETE-THE-DIVIDE', '4d80ef62-bbbb-49d0-8dac-3aad00fa37a7', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PROB_Grievance', 'd68d4014-e40f-49ea-aa33-2902bd017228', 'Active', 'probation', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC-PollChief', 'fb443447-de07-4d6d-b5c0-78ededed5880', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-MCD', '92d69d53-7726-416f-b860-4fc781b38908', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', 'e9f8b978-2124-4cf1-ab06-27d0a87a6394', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('SB_ANALYTICS_PROTO', '045c8256-9ebd-45ce-8444-fa147c555dbc', 'Active', 'isd , dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional', '4e873a9f-8b68-424c-854f-02b500338236', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-MCD-SDM', '3bb4a69f-e9bc-4495-9ee3-5bbd9f817798', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-CAB-eForms', 'fc0beaa3-0810-4f8a-8cf4-3fa49e880519', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-AVD-D350-DCFS', '4d89e736-dbfd-4b34-8914-1774a1fc61b4', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional', '3fae5358-077a-4295-8dad-1dfcb6e6f6a3', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1 d83bbf33-871b-4243-9601-b275072d00f0', 'd83bbf33-871b-4243-9601-b275072d00f0', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ECAVS_DR', 'b48c33e8-4acf-46f2-bef8-27660ec2cddd', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC Financial Accounting System', '3a23f80c-6435-442f-b0df-bf4435d45e6e', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', 'd9fe3828-7c5f-49ce-9056-9d8d85095eab', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Works Dev', '24cfccc3-023b-4787-8185-34c2e5dcff34', 'Active', 'pw', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', '2793798a-0aef-4d2f-acd5-af888baf35e5', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Pay-As-You-Go Dev/Test', '352eb59b-8a14-4fa9-8d35-ca36fadd50de', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', 'e82b259b-b37d-4584-ba28-4d671da80080', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', '8009ed9b-2074-4efa-bb45-e18ba606eac6', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC Systems Development', 'f2f6c1d0-ca5c-4882-ba08-d045b379411e', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS', '380e99f0-3b19-46c0-94f7-37cbf2b0a1c8', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', 'ee30faf0-4ec3-4198-a7e0-59227a4301b2', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AMO - Application Management Organization', 'dd62930a-c647-482d-97f8-e94fccdc69ee', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-RRCC_NOC', 'e128ba51-37b6-49e5-9f4f-90f84ab0ddbf', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-AgingDisabilities-CloudServices', '8666bdfc-18cf-40db-b665-242269fa7c78', 'Active', 'ad', 'azure', 'IPacheco@ad.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Works', '939f402a-d79e-45a8-892b-6804d0a02ea1', 'Active', 'pw', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ITSS_AVD-D435-DMH', 'ff349438-ef9b-46a4-831a-d314e7e00c73', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-TD-Backup', '48d3344e-f546-4706-bbae-40ba9ec46bae', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-CGO-CSA', 'e5649088-eaf8-4eee-a0fc-2fc9d6f6384c', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH-Integration-VSEnt-sub-Dev02', '2b249929-0fdf-4474-9929-ce56bbe56c97', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', 'fef3d54f-277a-41bc-85c5-6d4c9df4b108', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMHDPH_HIDEX_sub_Prod', '0fa0f99d-9e3d-4ed4-95d6-25e72eceb339', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCCVSAPDevOps', 'bde989d4-c9e3-4cb7-9792-077ba2dd14f0', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC Systems Development â€“ Production', 'f60b95f7-1af7-4857-9444-c2ddc279baf1', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Assessor ITD Dev', 'c1d1724f-462c-47c2-afef-309fdf3cb79f', 'Active', 'assessor', 'azure', 'ed.nersessian@assessor.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', 'a6e2de74-d4f9-45d0-a033-c151888e043f', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCCAppPrd', '63943293-54c2-425e-8a89-3fe0f7a95ad0', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '431942c4-af9a-4742-ad8e-f2abbad39437', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Probation WVD', '2363ef35-a33c-4190-99f5-49c7df68fcf2', 'Active', 'probation', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Pay-As-You-Go', '8c12bf5c-75fa-4589-86ce-ea915a8b7d1a', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '5aef17cc-107d-425b-83bf-49fde1805c7e', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC_ECBMS_TextToSpeach', 'cfb9ffdd-ec10-4b2c-a569-21244f9b6464', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', '934687eb-843e-40d7-aec0-71cf2d239e31', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-DHS-HR', '438b9161-6fcf-4014-8158-66f32d09abf2', 'Active', 'dhs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-RRCC_SAILPOINT', '55e5c7d8-df37-4c11-81a5-7241ba19b683', 'Active', 'rrcc', 'azure', 'SGadson@rrcc.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', '25f6681c-3271-4fea-ad14-e979c8110c17', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DCFS-Prod', '2857fc56-da97-428e-ba64-33d1ad16d615', 'Active', 'dcfs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-TD-OSS', 'a894e07b-aa30-4494-a78d-22283a74413c', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '501fb4bc-be99-402c-8f26-85a68f080f5d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ARTS - D365 F and O', '855b4cdf-0561-4495-964f-ef5e380efa08', 'Active', 'arts', 'azure', 'ACamins@arts.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH_DMBI_SUB_PROD', 'e08139a0-3f72-4070-a824-506dfdd952e4', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', 'df1451f5-8dd0-4987-892c-d2333da58d8d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMH_HIDEX_sub_Prod', '70e72205-7978-4185-8976-b3ae37701552', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ProbAzureComP01', 'd77d362c-d622-4ee5-8fb9-c01d6f88c5d3', 'Active', 'probation', 'azure', 'Angel.Orduno@probation.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', '69dbbe3e-26f1-421d-bf3b-818eee2c4f50', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('TTC', 'cd9a925f-656a-484c-8484-f9f99eb8b13a', 'Active', 'ttc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-B2C', 'dea56a75-9335-4cbf-b39a-0fdd3e777d09', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('District Attorney', '0b4a0319-26a1-4904-9bf6-b045ecfc645b', 'Active', 'da', 'azure', 'MattChavez@da.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DPH_HIDEX_sub_Dev', 'abafef4c-d3d1-41ef-b7ad-c304d2084882', 'Active', 'ph', 'azure', 'MHussain@ph.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Professional Subscription', 'ce0cbfc5-4841-460e-95a5-50f0d2d14528', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACJCOD_SUB_AZURE_PROD', '326c590d-2f4d-40a3-9e62-d596d75cc9a0', 'Active', 'jcod', 'azure', 'KLee@jcod.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TD-EIS-CLEANROOM', 'cd0da275-efbe-4bab-bb34-af3fdfe15155', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-AI_Enterprise', 'cb0d86a4-5280-4865-8f5e-a942637bb4e2', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', 'c1dcb007-d1e7-42fb-8f98-5b865980a1fb', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', 'c26860f6-ac82-4c40-b2a7-7221171f90b4', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-EADS', 'f944f190-ab70-49ac-94d0-2cec4e6518db', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '661719d1-26fd-4037-8d55-827e7eeca0c8', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('County Counsel', 'c70325d2-483e-4cb5-94be-813234c7ae7c', 'Active', 'counsel', 'azure', 'KKim@counsel.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMHDPH_HIDEX_sub_Dev', '14f73201-3f02-45e0-aa9f-2ccf4f7104d0', 'Active', 'ph,dmh', 'azure', 'jmokolo@ph.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DCFS-Dev', 'c2d5f634-4d89-4d78-971c-929aa89bdd98', 'Active', 'dcfs', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', 'def70a83-6cb0-462e-a664-200a0d46ca50', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-MARS', '319e4283-b2d3-42f7-8b5a-2772efc66652', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMHDPH_HIDEX_sub_QA', '965126b9-a5ce-4974-b238-7edaab03e70a', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('APD_BOX_CCMS_Integration', 'acce76ac-e5c3-4c49-a957-e9c19063fe6d', 'Active', 'apd', 'azure', 'rmgarcia@apd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ECAVS_Primary', 'bebe7ee2-f6ce-468d-a687-3bbb24d25c6d', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-AI_Kiro', 'ee6c840f-e4ef-4e9b-b9ad-4f0e4ca4944a', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Catchup', 'e897c0b6-d5be-4f86-8a9c-860565e6d513', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Pay-As-You-Go Dev/Test', '9125cc1d-3b5d-4000-be51-f4ff45d8c75c', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-ITSS-AVD-D300-DTD', '3811003b-38a6-41ab-8d58-2e643d9888a6', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Microsoft Azure Enterprise', '54cfb45f-f978-43e2-81b0-24f987a2afb6', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Defender', '0197386c-00fd-436c-82c7-0622c1acd402', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD', 'b59ad08c-93af-445a-89a6-6dceac840b64', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1', 'b36680e6-9510-448f-8191-f8ee1c57a335', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise', '5e4f08ef-9299-400d-9436-5808721a386b', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AppCentric POC', 'c911cd0b-ef8c-4460-b362-39acaecf28a0', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH_EntInf_sub_Dev', 'f4f6391b-995d-4205-aef9-dd421eca2a5d', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', 'ca62b124-afc1-438d-9564-3896d14ba17d', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH-Integration-EA-sub-Dev04', '87e68527-db9b-4513-a81f-6db178430b8f', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1aks', '5fa73179-9c3e-4923-bbec-d58b928e6876', 'Active', 'ph', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Assessor ITD Infrastructure', '160535e6-42c1-4fb4-90d3-2a3b1af885bb', 'Active', 'assessor', 'azure', 'ed.nersessian@assessor.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Probation', 'b98c5e0c-3504-476a-9ac3-249cda84591b', 'Active', 'probation', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACDMH-Integration-VSEnt-sub-Dev03', '75df7615-0fed-4993-a87d-5e9c6a120b1b', 'Active', 'dmh', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Conversion Technology', '749c7e17-92aa-42dd-9375-6f2c08555c5c', 'Active', 'pw', 'azure', 'AKOFFI@pw.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-CIO_Chief-Information-Office', 'e7685a82-9dce-417a-9093-9a4d955adac9', 'Active', 'cio ,isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCCHub', '41a2730c-23a1-41ec-b83d-932c06bb8f4c', 'Active', 'rrcc', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAC_DMH_HIDEX_sub_QA', 'cccf230c-c872-4a62-a7a5-560978421cc7', 'Active', 'isd', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACJCOD_SUB_AZURE', '7410b732-54d4-4ca5-8353-d99bd59400f7', 'Active', 'jcod', 'azure', 'RBringhurst@jcod.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Visual Studio Enterprise Subscription', 'f653d7c7-5667-4a83-8457-157e33ab9948', 'Active', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-GGSD_DM', '1c235d3e-f328-4988-ad69-226ceed875cc', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('BOS-WebApps-delete', 'a9e999e3-c310-4952-9cbc-bbcb65744c80', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF23', 'a0036f5a-eaa5-4f54-a438-67ebe1aff8c7', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF23', '187f9db0-c0e9-4759-8edd-5f6c82291bc7', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-NimithAI_Dev', '8900caaa-4a6d-40b0-904b-737451f6d4ea', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-pbears', 'fc9306f4-0b30-4036-989b-c307c5f2a1b5', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Production_Bears', 'e241d9af-efc8-4f26-93d4-bea8aa20b76f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-BigShow', 'f1c73d83-ff6c-4239-9af8-5d0dfbfbf920', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-NYK', 'c6ee00ee-e44e-40c9-b86c-cac8ba094a54', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-KlayThompson', '0b2e9af4-999f-4aad-bffd-49d228ec9fde', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_lakers', '5990acb0-aaea-4f77-8051-36897eb2ebc9', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_LAKERS', 'ee419c27-8cfd-4eb8-ad25-e0dba32a26f7', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-PolarBear', '8e632fb6-0b3a-42e1-b854-0d23e07b1a2d', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-pbears', '3fcd10a9-fc41-4a2e-9fad-586b2327b3c9', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-ManUnited', '0137af3a-049a-49d6-8d7d-33c9973fd79c', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Kyrie', 'ac2f5bb1-f600-4ae7-a31a-e464d20d0b1f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1', '6613d130-736c-47eb-b6e7-04f1ef4f1693', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF23', '7171382c-6aa8-414a-b8e3-5a8101d6a20e', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-Countywide-Info-Hub', '57897eb8-f82a-432f-919e-97935174f026', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_lakers', 'c528ae20-2ff8-45ae-91c5-0be781ee0910', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Chelsea', 'c8431256-ab46-4405-9468-5dd303f78b8a', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1', '14e75089-50df-465c-8689-96aa17272f43', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-CAB-POC', '26489a51-2668-43d4-b32c-99518bd13d69', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF77_LAKERS', '602eef48-0813-4766-837a-7364b7f36c19', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_LAKERS', '9751ffb8-68b9-4e18-bafc-95e6dc08ac54', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Lakers', '35e007b8-ce51-42ef-8bfb-11a751fc3934', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_lakers', '338850b2-a741-4d5a-8ffc-aaa8c6ac73ed', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-YOUT', 'd08ef28e-7605-4e8b-a301-80ab45cf4178', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-PB77', '0f172d9b-e0e5-4c3d-b294-e1ee919a399f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-EntStage1', '506c02ed-8bbb-402e-897a-00e84fc03d26', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-KlayThompson12', 'f8161d7e-b0c1-4f96-aadc-d8c2eacd7e86', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-NBA_recon', '0a0d158c-8b5c-4321-99cc-2a8a120f8fd9', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TerraformIni', '0cf2d03a-8814-4919-9261-f60d322ff0b8', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-LAKERS', 'e335a5cf-3ab3-4f6d-adab-0947b68a4be8', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-NimithAI_Dev', '7c047701-e3d3-4703-befd-76e52ba80a58', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-RHINO56', '19564149-54d3-4a72-81a7-a2595541b19f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF23', '71034932-366f-4c8a-a159-7c376c5e6de3', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-LAKESHOW', '97ce8bf5-a627-4442-b23d-a83b98f11a31', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Kobe', '64ab936d-1e22-4ac4-a77d-2075f516bdf0', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Production_Bears', '8c4ac84b-84a4-45e9-89e5-38c04a8ef1fb', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PB55', '31bddbaa-ad43-4105-ab29-1bdf775db216', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Arsenal', 'd3d82339-6857-4014-8952-e5ba2165477b', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure ProbAI', 'ac2b7ee2-c00b-454f-b848-30d407d9ba37', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TerraformIni', '31c46eb4-41cf-4723-8f8e-14604d71e157', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PB55', '2589be4e-c19f-49f5-9ffc-5fd131e4b5f1', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-DBZ', 'ef6dd5be-c102-4634-9fdc-510c8146959f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Azure subscription 1', '6e7f8efb-029c-4a92-9a0d-16f5645a5038', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF23', 'c4509fcb-2a01-45c6-b339-61ebd3cb641b', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_lakers', '9f3cf707-5ac7-4324-8696-b74e2d8abedd', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-TF_lakers', 'e4d43db6-7466-40b0-9cb1-41b7c55f54ec', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-eCloud', 'cbc760f1-a325-4ae3-b822-b0a7f9f47e82', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-eCloud', '496db95b-ed11-40da-b630-ff215bb38be2', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Unrivaled', 'c1065c7a-bfc6-4e65-b0d3-faba1cc4735f', 'Disabled', '', 'azure', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AZU-ISD-Curry', 'c15d079c-a452-4d31-8708-668f59b901d4', 'Disabled', '', 'azure', NULL);

GO

-- ── AWS ACCOUNTS ──────────────────────────────────────────────────────────────
-- Rows whose account ID is already known (extracted from spreadsheet):
PRINT 'Inserting AWS accounts (with IDs)...';
GO

INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PolarBear44', '100035083132', 'Active', 'isd', 'aws', 'lacisd_cloud_polarbear44@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PolarBear22', '074275212561', 'Active', 'isd', 'aws', 'lacisd_cloud_isd_polarbear22@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Terraform_Pri', '210454360575', 'Active', 'isd', 'aws', 'lacisd_cloud_rrcc7772@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Catchup8', '292398627634', 'Active', 'isd', 'aws', 'lacisd_cloud_Catchup8@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PB55', '582866709502', 'Active', 'isd', 'aws', 'lacisd_cloud_polarbear55@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Catchup5', '578761488822', 'Active', 'isd', 'aws', 'lacisd_cloud_Catchup5@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-CatchUp', '578761488664', 'Active', 'isd', 'aws', 'lacisd_cloud_CatchUp@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Terraform_Pri', '738245087506', 'Active', 'isd', 'aws', 'lacisd_cloud_rrcc_772@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Catchup10', '748134080874', 'Active', 'isd', 'aws', 'lacisd_cloud_Catchup10@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-RHINO77', '772469157592', 'Active', 'isd', 'aws', 'lacisd_cloud_rhino77@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-PB559', '930936105004', 'Active', 'isd', 'aws', 'lacisd_cloud_PB559@isd.lacounty.gov');
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-Catchup7', '987020211993', 'Active', 'isd', 'aws', 'lacisd_cloud_Catchup7@isd.lacounty.gov');

GO

-- ── AWS ACCOUNTS (ID pending) ─────────────────────────────────────────────────
-- The following accounts appear in the spreadsheet but no account ID was recorded.
-- subscription_id is left NULL; update these rows once the IDs are confirmed.
--
-- Example update:
--   UPDATE portal.portal_department_resources
--   SET subscription_id = '<12-digit-account-id>', updated_at_utc = SYSUTCDATETIME()
--   WHERE subscription_name = '<account-name>' AND cloud = 'aws';
PRINT 'Inserting AWS accounts (ID pending)...';
GO

INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD IDD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Coroner', NULL, 'Active', 'coroner', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS_AWS_Enterprise', NULL, 'Active', 'dhs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Health - Pinpoint', NULL, 'Active', 'ph', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD Telecom', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('magostinelliWDACS', NULL, 'Active', 'ad', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AAB_CONNECT-DEV', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Defender IT Agency', NULL, 'Active', 'pubdef', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ENTERPRISE SECURITY', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AUDITOR_CONNECT-TEST', NULL, 'Active', 'auditor', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ITSS AppStream', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ASESSOR_DEV', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DPSS-AWS-Connect', NULL, 'Active', 'dpss', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AAB_CONNECT-PROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AAB_CONNECT-TEST', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DEO AWS', NULL, 'Active', 'opportunity', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DCFS', NULL, 'Active', 'dcfs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC-AWS-S3', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD Secure Access Engineering', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC-ACGR', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-CatchUp1', NULL, 'Active', '', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AUDITOR_CONNECT-PROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('District_Attorney-AWS_Connect', NULL, 'Active', 'da', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-DMZ-Web-test-1', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-FIRE-PROD', NULL, 'Active', 'fire', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TDEIS-TEST', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD Openshift', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('lac-abc-primary', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACJCOD_SUB_AWS', NULL, 'Active', 'jcod', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ECRC_CONNECT-DEV', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LAISD - Backup Storage', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD GGSD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-RRCC_VSD_SANDBOX', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TREASURY_TAX_CONNECT-DEV', NULL, 'Active', 'ttc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TREASURY_TAX', NULL, 'Active', 'ttc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ecloudtest', NULL, 'Active', '', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('IDD Websites', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('eGIS_ArcGIS_Enterprise', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('IDD GIS Caltrap', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS Connect - CleanLA', NULL, 'Active', 'dpw', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PUBLIC DEFENDER', NULL, 'Active', 'pubdef', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CED-ESE', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISAB', NULL, 'Active', 'isab', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-SECURITY_PaloAltoPOC', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-DCFS-Oracle', NULL, 'Active', 'dcfs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Audit', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACERA_Dev', NULL, 'Active', 'lacera', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACERA', NULL, 'Active', 'lacera', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACountyISD_Workspaces', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC - LAVOTE ELECTION RESULTS', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-SECURITY_PaloAltoPROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ASESSOR_TEST', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('GIS_Cloud_Platform', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-SSB-CSI', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('County of Los Angeles, DPSS', NULL, 'Active', 'dpss', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACounty-ISAB - cjistables', NULL, 'Active', 'isab', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS_Private_5G_Dev', NULL, 'Active', 'dhs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DPSS ITD Network Management', NULL, 'Active', 'dpss', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PaloAlto-DMZ', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PUBLIC WORKS', NULL, 'Active', 'pw', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('District Attorney', NULL, 'Active', 'da', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Consumer & Business Affairs', NULL, 'Active', 'dcba', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD MCD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD IDD Managed', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('LACounty Diversion', NULL, 'Active', 'dhs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DPSS', NULL, 'Active', 'dpss', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Assessor', NULL, 'Active', 'assessor', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Log archive', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('SharedServices', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ASESSOR_PROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('SSB-EGIS', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DHS-VMC', NULL, 'Active', 'dhs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DLT LA County', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Human Resources', NULL, 'Active', 'hr', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD TD eCloud', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Subpoena', NULL, 'Active', 'isab', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PaloAlto-DMZ', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-DPW-PROJECT_SANDBOX', NULL, 'Active', 'dpw', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC - AWS Connect Elections', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Military_and_Veterans_Affairs', NULL, 'Active', 'mva', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-RRCC_DW_ELECTION-POC', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ASESSOR_Veeam', NULL, 'Active', 'assessor', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ENTERPRISE NETWORKING', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-CGO_CSA_IR', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PUBLIC_DEFENDER_CONNECT-TEST', NULL, 'Active', 'pubdef', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-CAB', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-FIRE-DEV', NULL, 'Active', 'fire', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CaaS ECM EKS Project', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ENTERPRISE INFRASTRUCTURE', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS CONNECT', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Mainframe_VTS', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC - AWS Connect', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Animal Care', NULL, 'Active', 'animalcare', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ISD-GGSD-ISDHR', NULL, 'Active', '', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ECRC_CONNECT-PROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TREASURY_TAX _CONNECT-PROD', NULL, 'Active', 'ttc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PUBLIC_DEFENDER _CONNECT-PROD', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TD_OSS_LPS', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PW_DISPATCH_CONNECT', NULL, 'Active', 'dpw', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-TREASURY_TAX_CONNECT-TEST', NULL, 'Active', 'ttc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC_DEV_TEST', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ITSS_Share', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Public Health', NULL, 'Active', 'ph', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Probation', NULL, 'Active', 'probation', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PUBLIC INFRASTRUCTURE SERVICES', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-ISD-NBA_youngboy', NULL, 'Active', '', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-IRSD_BeOn', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-CaaS_Rancher_Production', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PaloAlto-Ingress', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('DCFS Dev', NULL, 'Active', 'dcfs', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Planning', NULL, 'Active', 'planning', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-RRCC_ADMIN_SANDBOX', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('PUBLIC SERVICES POC', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('ENTERPRISE AUDITING', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('RRCC Hoth - Production', NULL, 'Active', 'rrcc', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('CaaS-Rancher-Non-prod', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PUBLIC_DEFENDER_CONNECT-DEV', NULL, 'Active', 'pubdef', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-AUDITOR_CONNECT-DEV', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-PubLib-MediaArchive', NULL, 'Active', 'library', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('Library', NULL, 'Active', 'library', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('APD-AWS1', NULL, 'Active', 'apd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('AWS-Monitoring', NULL, 'Active', 'isd', 'aws', NULL);
INSERT INTO portal.portal_department_resources (subscription_name, subscription_id, status, department, cloud, sample_mail)
VALUES ('SSB EGIS CAMS', NULL, 'Active', 'isd', 'aws', NULL);

GO

PRINT 'Done. Verify with:';
PRINT '  SELECT department, cloud, COUNT(*) AS cnt FROM portal.portal_department_resources GROUP BY department, cloud ORDER BY department, cloud;';
GO
