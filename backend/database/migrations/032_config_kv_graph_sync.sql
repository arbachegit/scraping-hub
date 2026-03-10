-- Migration: 032_config_kv_graph_sync
-- Creates config_kv table for graph sync state tracking
-- Used by graph-sync.js to store last sync timestamp

CREATE TABLE IF NOT EXISTS config_kv (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auto-update updated_at on change
CREATE OR REPLACE FUNCTION update_config_kv_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS config_kv_updated_at ON config_kv;
CREATE TRIGGER config_kv_updated_at
  BEFORE UPDATE ON config_kv
  FOR EACH ROW
  EXECUTE FUNCTION update_config_kv_timestamp();

-- Initial graph sync entry
INSERT INTO config_kv (key, value)
VALUES ('graph_sync_last_run', NOW()::TEXT)
ON CONFLICT (key) DO NOTHING;
