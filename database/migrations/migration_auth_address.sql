-- Migration: Add address fields to users table for profile completion
-- Date: 2026-02-27
-- Purpose: Users complete their profile with CEP + address after first login

ALTER TABLE users ADD COLUMN IF NOT EXISTS cep VARCHAR(9);
ALTER TABLE users ADD COLUMN IF NOT EXISTS logradouro VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS numero VARCHAR(20);
ALTER TABLE users ADD COLUMN IF NOT EXISTS complemento VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS bairro VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS cidade VARCHAR(100);
ALTER TABLE users ADD COLUMN IF NOT EXISTS uf VARCHAR(2);
