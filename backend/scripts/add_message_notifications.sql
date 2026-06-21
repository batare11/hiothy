\set ON_ERROR_STOP on

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20) NOT NULL DEFAULT 'info',
    ADD COLUMN IF NOT EXISTS related_record_id INTEGER,
    ADD COLUMN IF NOT EXISTS action_type VARCHAR(30),
    ADD COLUMN IF NOT EXISTS action_path VARCHAR(300),
    ADD COLUMN IF NOT EXISTS dedupe_key VARCHAR(150);

CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_dedupe_key
    ON messages (dedupe_key);

COMMENT ON COLUMN messages.severity IS
    '消息风险级别：info、warning、high、critical';
COMMENT ON COLUMN messages.related_record_id IS
    '关联的血压记录 ID';
COMMENT ON COLUMN messages.dedupe_key IS
    '自动消息唯一键，用于防止重复提醒';
