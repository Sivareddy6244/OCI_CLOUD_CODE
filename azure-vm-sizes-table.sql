-- ============================================================
-- FILE: Create and seed portal.azure_vm_sizes table
-- ============================================================
-- Purpose : Stores the list of Azure VM sizes that are available
--           to users in the portal.  Administrators can add, remove,
--           or temporarily disable sizes by updating rows in this
--           table without any code deployments.
--
-- Columns:
--   name       - Azure VM size name  (e.g. Standard_D2s_v3)
--   vcpus      - Number of virtual CPUs
--   memory_mb  - RAM in megabytes
--   is_active  - 1 = show to users, 0 = hidden (soft-delete)
--   sort_order - Display order in the dropdown (lower = first)
--
-- Run once against the Azure SQL database (portal schema).
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
    AND    t.name = 'azure_vm_sizes'
)
BEGIN
    CREATE TABLE portal.azure_vm_sizes (
        id         INT           IDENTITY(1,1) NOT NULL,
        name       NVARCHAR(64)  NOT NULL,
        vcpus      INT           NOT NULL,
        memory_mb  INT           NOT NULL,
        is_active  BIT           NOT NULL CONSTRAINT DF_azure_vm_sizes_is_active  DEFAULT 1,
        sort_order INT           NOT NULL CONSTRAINT DF_azure_vm_sizes_sort_order DEFAULT 0,
        CONSTRAINT PK_azure_vm_sizes      PRIMARY KEY CLUSTERED (id),
        CONSTRAINT UQ_azure_vm_sizes_name UNIQUE (name),
        CONSTRAINT CK_azure_vm_sizes_vcpus   CHECK (vcpus > 0),
        CONSTRAINT CK_azure_vm_sizes_memory  CHECK (memory_mb > 0),
        CONSTRAINT CK_azure_vm_sizes_sort    CHECK (sort_order >= 0)
    );
END
GO

-- ── Seed initial data (safe to re-run: only inserts if name not present) ──────
-- Burstable B-series
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2s',    2,  4096, 10 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2ms',   2,  8192, 11 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B4ms',   4, 16384, 12 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B4ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B8ms',   8, 32768, 13 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B8ms');
-- General Purpose D-series v3
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2s_v3',  2,   8192, 20 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4s_v3',  4,  16384, 21 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8s_v3',  8,  32768, 22 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16s_v3', 16,  65536, 23 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32s_v3', 32, 131072, 24 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64s_v3', 64, 262144, 25 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64s_v3');
-- General Purpose D-series v4 Intel
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2s_v4',  2,   8192, 30 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4s_v4',  4,  16384, 31 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8s_v4',  8,  32768, 32 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16s_v4', 16,  65536, 33 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32s_v4', 32, 131072, 34 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32s_v4');
-- General Purpose D-series v4 AMD
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2as_v4',  2,   8192, 40 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4as_v4',  4,  16384, 41 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8as_v4',  8,  32768, 42 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16as_v4', 16,  65536, 43 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32as_v4', 32, 131072, 44 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64as_v4', 64, 262144, 45 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64as_v4');
-- General Purpose D-series v5 Intel
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2s_v5',  2,   8192, 50 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4s_v5',  4,  16384, 51 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8s_v5',  8,  32768, 52 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16s_v5', 16,  65536, 53 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32s_v5', 32, 131072, 54 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32s_v5');
-- General Purpose D-series v5 AMD
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2as_v5',  2,   8192, 60 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4as_v5',  4,  16384, 61 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8as_v5',  8,  32768, 62 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16as_v5', 16,  65536, 63 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32as_v5', 32, 131072, 64 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64as_v5', 64, 262144, 65 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64as_v5');
-- Memory Optimized E-series v3
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2s_v3',  2,   16384, 70 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4s_v3',  4,   32768, 71 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8s_v3',  8,   65536, 72 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16s_v3', 16, 131072, 73 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32s_v3', 32, 262144, 74 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32s_v3');
-- Memory Optimized E-series v4 AMD
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2as_v4',  2,   16384, 80 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4as_v4',  4,   32768, 81 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8as_v4',  8,   65536, 82 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16as_v4', 16, 131072, 83 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32as_v4', 32, 262144, 84 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32as_v4');
-- Memory Optimized E-series v5 AMD
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2as_v5',  2,   16384, 90 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4as_v5',  4,   32768, 91 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8as_v5',  8,   65536, 92 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16as_v5', 16, 131072, 93 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32as_v5', 32, 262144, 94 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32as_v5');
-- Compute Optimized F-series v2
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F2s_v2',  2,  4096, 100 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F2s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F4s_v2',  4,  8192, 101 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F4s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F8s_v2',  8, 16384, 102 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F8s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F16s_v2', 16, 32768, 103 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F16s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F32s_v2', 32, 65536, 104 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F32s_v2');

-- Additional sizes from excel/azure_vm_sizes 1.xlsx with vCPU/memory sourced from Azure SKU metadata.
-- Safe to re-run: idempotent inserts by name.
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B12ms', 12, 49152, 200 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B12ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B16als_v2', 16, 32768, 201 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B16als_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B16as_v2', 16, 65536, 202 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B16as_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B16ls_v2', 16, 32768, 203 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B16ls_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B16ms', 16, 65536, 204 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B16ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B16s_v2', 16, 65536, 205 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B16s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B1ls', 1, 512, 206 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B1ls');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B1ms', 1, 2048, 207 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B1ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B1s', 1, 1024, 208 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B1s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B20ms', 20, 81920, 209 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B20ms');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2als_v2', 2, 4096, 210 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2als_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2as_v2', 2, 8192, 211 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2as_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2ats_v2', 2, 1024, 212 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2ats_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2ls_v2', 2, 4096, 213 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2ls_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2s_v2', 2, 8192, 214 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B2ts_v2', 2, 1024, 215 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B2ts_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B32als_v2', 32, 65536, 216 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B32als_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B32as_v2', 32, 131072, 217 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B32as_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B32ls_v2', 32, 65536, 218 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B32ls_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B32s_v2', 32, 131072, 219 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B32s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B4als_v2', 4, 8192, 220 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B4als_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B4as_v2', 4, 16384, 221 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B4as_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B4ls_v2', 4, 8192, 222 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B4ls_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B4s_v2', 4, 16384, 223 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B4s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B8als_v2', 8, 16384, 224 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B8als_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B8as_v2', 8, 32768, 225 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B8as_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B8ls_v2', 8, 16384, 226 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B8ls_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_B8s_v2', 8, 32768, 227 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_B8s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16_v4', 16, 65536, 228 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16_v5', 16, 65536, 229 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16a_v4', 16, 65536, 230 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16ads_v5', 16, 65536, 231 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16d_v4', 16, 65536, 232 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16d_v5', 16, 65536, 233 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16ds_v4', 16, 65536, 234 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16ds_v5', 16, 65536, 235 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16lds_v5', 16, 32768, 236 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D16ls_v5', 16, 32768, 237 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D16ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2_v4', 2, 8192, 238 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2_v5', 2, 8192, 239 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2a_v4', 2, 8192, 240 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2ads_v5', 2, 8192, 241 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2d_v4', 2, 8192, 242 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2d_v5', 2, 8192, 243 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2ds_v4', 2, 8192, 244 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2ds_v5', 2, 8192, 245 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2lds_v5', 2, 4096, 246 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D2ls_v5', 2, 4096, 247 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D2ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32_v4', 32, 131072, 248 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32_v5', 32, 131072, 249 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32a_v4', 32, 131072, 250 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32ads_v5', 32, 131072, 251 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32d_v4', 32, 131072, 252 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32d_v5', 32, 131072, 253 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32ds_v4', 32, 131072, 254 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32ds_v5', 32, 131072, 255 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32lds_v5', 32, 65536, 256 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D32ls_v5', 32, 65536, 257 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D32ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48_v4', 48, 196608, 258 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48_v5', 48, 196608, 259 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48a_v4', 48, 196608, 260 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48ads_v5', 48, 196608, 261 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48as_v4', 48, 196608, 262 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48as_v5', 48, 196608, 263 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48d_v4', 48, 196608, 264 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48d_v5', 48, 196608, 265 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48ds_v4', 48, 196608, 266 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48ds_v5', 48, 196608, 267 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48lds_v5', 48, 98304, 268 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48ls_v5', 48, 98304, 269 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48s_v3', 48, 196608, 270 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48s_v4', 48, 196608, 271 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D48s_v5', 48, 196608, 272 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D48s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4_v4', 4, 16384, 273 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4_v5', 4, 16384, 274 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4a_v4', 4, 16384, 275 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4ads_v5', 4, 16384, 276 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4d_v4', 4, 16384, 277 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4d_v5', 4, 16384, 278 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4ds_v4', 4, 16384, 279 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4ds_v5', 4, 16384, 280 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4lds_v5', 4, 8192, 281 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D4ls_v5', 4, 8192, 282 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D4ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64_v4', 64, 262144, 283 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64_v5', 64, 262144, 284 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64a_v4', 64, 262144, 285 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64ads_v5', 64, 262144, 286 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64d_v4', 64, 262144, 287 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64d_v5', 64, 262144, 288 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64ds_v4', 64, 262144, 289 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64ds_v5', 64, 262144, 290 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64lds_v5', 64, 131072, 291 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64ls_v5', 64, 131072, 292 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64s_v4', 64, 262144, 293 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D64s_v5', 64, 262144, 294 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D64s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8_v4', 8, 32768, 295 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8_v5', 8, 32768, 296 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8a_v4', 8, 32768, 297 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8ads_v5', 8, 32768, 298 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8d_v4', 8, 32768, 299 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8d_v5', 8, 32768, 300 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8ds_v4', 8, 32768, 301 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8ds_v5', 8, 32768, 302 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8lds_v5', 8, 16384, 303 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D8ls_v5', 8, 16384, 304 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D8ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96_v5', 96, 393216, 305 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96a_v4', 96, 393216, 306 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96ads_v5', 96, 393216, 307 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96as_v4', 96, 393216, 308 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96as_v5', 96, 393216, 309 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96d_v5', 96, 393216, 310 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96ds_v5', 96, 393216, 311 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96lds_v5', 96, 196608, 312 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96lds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96ls_v5', 96, 196608, 313 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96ls_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_D96s_v5', 96, 393216, 314 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_D96s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS11-1_v2', 1, 14336, 315 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS11-1_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS11_v2', 2, 14336, 316 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS11_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS12-1_v2', 1, 28672, 317 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS12-1_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS12-2_v2', 2, 28672, 318 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS12-2_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS12_v2', 4, 28672, 319 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS12_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS13-2_v2', 2, 57344, 320 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS13-2_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS13-4_v2', 4, 57344, 321 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS13-4_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS13_v2', 8, 57344, 322 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS13_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS14-4_v2', 4, 114688, 323 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS14-4_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS14-8_v2', 8, 114688, 324 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS14-8_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS14_v2', 16, 114688, 325 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS14_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS1_v2', 1, 3584, 326 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS1_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS2_v2', 2, 7168, 327 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS2_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS3_v2', 4, 14336, 328 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS3_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS4_v2', 8, 28672, 329 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS4_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_DS5_v2', 16, 57344, 330 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_DS5_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E104i_v5', 104, 688128, 331 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E104i_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E104id_v5', 104, 688128, 332 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E104id_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E104ids_v5', 104, 688128, 333 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E104ids_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E104is_v5', 104, 688128, 334 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E104is_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E112ias_v5', 112, 688128, 335 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E112ias_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4ads_v5', 4, 131072, 336 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4as_v4', 4, 131072, 337 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4as_v5', 4, 131072, 338 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4ds_v4', 4, 131072, 339 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4ds_v5', 4, 131072, 340 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4s_v3', 4, 131072, 341 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4s_v4', 4, 131072, 342 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-4s_v5', 4, 131072, 343 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-4s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8ads_v5', 8, 131072, 344 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8as_v4', 8, 131072, 345 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8as_v5', 8, 131072, 346 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8ds_v4', 8, 131072, 347 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8ds_v5', 8, 131072, 348 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8s_v3', 8, 131072, 349 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8s_v4', 8, 131072, 350 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16-8s_v5', 8, 131072, 351 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16-8s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16_v4', 16, 131072, 352 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16_v5', 16, 131072, 353 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16a_v4', 16, 131072, 354 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16ads_v5', 16, 131072, 355 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16bds_v5', 16, 131072, 356 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16bs_v5', 16, 131072, 357 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16d_v4', 16, 131072, 358 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16d_v5', 16, 131072, 359 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16ds_v4', 16, 131072, 360 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16ds_v5', 16, 131072, 361 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16s_v4', 16, 131072, 362 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E16s_v5', 16, 131072, 363 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E16s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20_v4', 20, 163840, 364 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20_v5', 20, 163840, 365 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20a_v4', 20, 163840, 366 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20ads_v5', 20, 163840, 367 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20as_v4', 20, 163840, 368 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20as_v5', 20, 163840, 369 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20d_v4', 20, 163840, 370 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20d_v5', 20, 163840, 371 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20ds_v4', 20, 163840, 372 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20ds_v5', 20, 163840, 373 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20s_v3', 20, 163840, 374 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20s_v4', 20, 163840, 375 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E20s_v5', 20, 163840, 376 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E20s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2_v5', 2, 16384, 377 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2a_v4', 2, 16384, 378 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2ads_v5', 2, 16384, 379 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2bds_v5', 2, 16384, 380 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2bs_v5', 2, 16384, 381 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2d_v4', 2, 16384, 382 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2d_v5', 2, 16384, 383 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2ds_v4', 2, 16384, 384 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2ds_v5', 2, 16384, 385 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2s_v4', 2, 16384, 386 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E2s_v5', 2, 16384, 387 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E2s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16ads_v5', 16, 262144, 388 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16as_v4', 16, 262144, 389 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16as_v5', 16, 262144, 390 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16ds_v4', 16, 262144, 391 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16ds_v5', 16, 262144, 392 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16s_v3', 16, 262144, 393 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16s_v4', 16, 262144, 394 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-16s_v5', 16, 262144, 395 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-16s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8ads_v5', 8, 262144, 396 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8as_v4', 8, 262144, 397 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8as_v5', 8, 262144, 398 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8ds_v4', 8, 262144, 399 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8ds_v5', 8, 262144, 400 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8s_v3', 8, 262144, 401 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8s_v4', 8, 262144, 402 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32-8s_v5', 8, 262144, 403 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32-8s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32_v4', 32, 262144, 404 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32_v5', 32, 262144, 405 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32a_v4', 32, 262144, 406 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32ads_v5', 32, 262144, 407 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32bds_v5', 32, 262144, 408 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32bs_v5', 32, 262144, 409 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32d_v4', 32, 262144, 410 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32d_v5', 32, 262144, 411 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32ds_v4', 32, 262144, 412 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32ds_v5', 32, 262144, 413 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32s_v4', 32, 262144, 414 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E32s_v5', 32, 262144, 415 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E32s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2ads_v5', 2, 32768, 416 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2as_v4', 2, 32768, 417 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2as_v5', 2, 32768, 418 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2ds_v4', 2, 32768, 419 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2ds_v5', 2, 32768, 420 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2s_v3', 2, 32768, 421 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2s_v4', 2, 32768, 422 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4-2s_v5', 2, 32768, 423 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4-2s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48_v4', 48, 393216, 424 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48_v5', 48, 393216, 425 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48a_v4', 48, 393216, 426 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48ads_v5', 48, 393216, 427 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48as_v4', 48, 393216, 428 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48as_v5', 48, 393216, 429 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48bds_v5', 48, 393216, 430 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48bs_v5', 48, 393216, 431 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48d_v4', 48, 393216, 432 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48d_v5', 48, 393216, 433 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48ds_v4', 48, 393216, 434 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48ds_v5', 48, 393216, 435 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48s_v3', 48, 393216, 436 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48s_v4', 48, 393216, 437 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E48s_v5', 48, 393216, 438 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E48s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4_v4', 4, 32768, 439 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4_v5', 4, 32768, 440 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4a_v4', 4, 32768, 441 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4ads_v5', 4, 32768, 442 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4bds_v5', 4, 32768, 443 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4bs_v5', 4, 32768, 444 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4d_v4', 4, 32768, 445 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4d_v5', 4, 32768, 446 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4ds_v4', 4, 32768, 447 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4ds_v5', 4, 32768, 448 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4s_v4', 4, 32768, 449 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E4s_v5', 4, 32768, 450 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E4s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16ads_v5', 16, 524288, 451 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16as_v4', 16, 524288, 452 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16as_v5', 16, 524288, 453 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16ds_v4', 16, 516096, 454 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16ds_v5', 16, 524288, 455 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16s_v3', 16, 442368, 456 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16s_v4', 16, 516096, 457 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-16s_v5', 16, 524288, 458 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-16s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32ads_v5', 32, 524288, 459 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32as_v4', 32, 524288, 460 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32as_v5', 32, 524288, 461 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32ds_v4', 32, 516096, 462 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32ds_v5', 32, 524288, 463 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32s_v3', 32, 442368, 464 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32s_v4', 32, 516096, 465 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64-32s_v5', 32, 524288, 466 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64-32s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64_v4', 64, 516096, 467 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64_v5', 64, 524288, 468 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64a_v4', 64, 524288, 469 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64ads_v5', 64, 524288, 470 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64as_v4', 64, 524288, 471 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64as_v5', 64, 524288, 472 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64bds_v5', 64, 524288, 473 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64bs_v5', 64, 524288, 474 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64d_v4', 64, 516096, 475 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64d_v5', 64, 524288, 476 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64ds_v4', 64, 516096, 477 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64ds_v5', 64, 524288, 478 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64is_v3', 64, 442368, 479 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64is_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64s_v3', 64, 442368, 480 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64s_v4', 64, 516096, 481 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E64s_v5', 64, 524288, 482 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E64s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2ads_v5', 2, 65536, 483 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2as_v4', 2, 65536, 484 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2as_v5', 2, 65536, 485 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2ds_v4', 2, 65536, 486 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2ds_v5', 2, 65536, 487 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2s_v3', 2, 65536, 488 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2s_v4', 2, 65536, 489 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-2s_v5', 2, 65536, 490 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-2s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4ads_v5', 4, 65536, 491 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4as_v4', 4, 65536, 492 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4as_v5', 4, 65536, 493 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4ds_v4', 4, 65536, 494 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4ds_v5', 4, 65536, 495 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4s_v3', 4, 65536, 496 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4s_v4', 4, 65536, 497 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8-4s_v5', 4, 65536, 498 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8-4s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E80ids_v4', 80, 516096, 499 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E80ids_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E80is_v4', 80, 516096, 500 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E80is_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8_v4', 8, 65536, 501 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8_v5', 8, 65536, 502 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8a_v4', 8, 65536, 503 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8ads_v5', 8, 65536, 504 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8bds_v5', 8, 65536, 505 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8bs_v5', 8, 65536, 506 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8d_v4', 8, 65536, 507 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8d_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8d_v5', 8, 65536, 508 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8ds_v4', 8, 65536, 509 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8ds_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8ds_v5', 8, 65536, 510 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8s_v4', 8, 65536, 511 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8s_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E8s_v5', 8, 65536, 512 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E8s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-24ads_v5', 24, 688128, 513 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-24ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-24as_v4', 24, 688128, 514 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-24as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-24as_v5', 24, 688128, 515 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-24as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-24ds_v5', 24, 688128, 516 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-24ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-24s_v5', 24, 688128, 517 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-24s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-48ads_v5', 48, 688128, 518 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-48ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-48as_v4', 48, 688128, 519 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-48as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-48as_v5', 48, 688128, 520 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-48as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-48ds_v5', 48, 688128, 521 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-48ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96-48s_v5', 48, 688128, 522 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96-48s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96_v5', 96, 688128, 523 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96a_v4', 96, 688128, 524 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96a_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96ads_v5', 96, 688128, 525 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96ads_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96as_v4', 96, 688128, 526 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96as_v4');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96as_v5', 96, 688128, 527 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96as_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96bds_v5', 96, 688128, 528 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96bds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96bs_v5', 96, 688128, 529 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96bs_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96d_v5', 96, 688128, 530 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96d_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96ds_v5', 96, 688128, 531 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96ds_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_E96s_v5', 96, 688128, 532 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_E96s_v5');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F16s', 16, 32768, 533 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F16s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F1s', 1, 2048, 534 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F1s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F2s', 2, 4096, 535 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F2s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F48s_v2', 48, 98304, 536 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F48s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F4s', 4, 8192, 537 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F4s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F64s_v2', 64, 131072, 538 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F64s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F72s_v2', 72, 147456, 539 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F72s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_F8s', 8, 16384, 540 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_F8s');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_HC44-16rs', 16, 360448, 541 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_HC44-16rs');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_HC44-32rs', 32, 360448, 542 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_HC44-32rs');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_HC44rs', 44, 360448, 543 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_HC44rs');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L16as_v3', 16, 131072, 544 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L16as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L16s_v2', 16, 131072, 545 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L16s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L16s_v3', 16, 131072, 546 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L16s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L32as_v3', 32, 262144, 547 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L32as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L32s_v2', 32, 262144, 548 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L32s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L32s_v3', 32, 262144, 549 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L32s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L48as_v3', 48, 393216, 550 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L48as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L48s_v2', 48, 393216, 551 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L48s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L48s_v3', 48, 393216, 552 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L48s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L64as_v3', 64, 524288, 553 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L64as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L64s_v2', 64, 524288, 554 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L64s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L64s_v3', 64, 524288, 555 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L64s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L80as_v3', 80, 655360, 556 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L80as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L80s_v2', 80, 655360, 557 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L80s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L80s_v3', 80, 655360, 558 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L80s_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L8as_v3', 8, 65536, 559 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L8as_v3');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L8s_v2', 8, 65536, 560 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L8s_v2');
INSERT INTO portal.azure_vm_sizes (name, vcpus, memory_mb, sort_order) SELECT 'Standard_L8s_v3', 8, 65536, 561 WHERE NOT EXISTS (SELECT 1 FROM portal.azure_vm_sizes WHERE name = 'Standard_L8s_v3');
GO
