-- Migration 017: Create messaging_logs table
-- Auth Phase 1: Twilio + Infobip messaging integration
-- Tracks all outbound messages (WhatsApp, SMS, Email)

CREATE TABLE IF NOT EXISTS messaging_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    channel VARCHAR(20) NOT NULL CHECK (channel IN ('whatsapp', 'sms', 'email')),
    provider VARCHAR(20) NOT NULL CHECK (provider IN ('twilio', 'infobip', 'smtp', 'dev')),
    recipient TEXT NOT NULL,
    message_type VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('sent', 'failed', 'fallback')),
    error_message TEXT,
    provider_message_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_messaging_user ON messaging_logs(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_messaging_status ON messaging_logs(status, created_at DESC);
