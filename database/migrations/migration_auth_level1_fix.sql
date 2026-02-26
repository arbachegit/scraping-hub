-- =============================================================
-- Migration: Auth Level 1 Fix — role → is_admin
-- Date: 2026-02-26
-- Description: Remove role VARCHAR column, add is_admin BOOLEAN
-- Compatibility: SERIAL IDs (integer), NOT UUID
-- =============================================================

-- 1. Add is_admin column (idempotent)
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT false;

-- 2. Migrate data: role IN ('super_admin', 'admin') → is_admin = true
UPDATE users SET is_admin = true WHERE role IN ('super_admin', 'admin');

-- 3. Drop role column (Level 1 does not use roles)
ALTER TABLE users DROP COLUMN IF EXISTS role;
