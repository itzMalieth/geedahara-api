-- Phase 4 Migration: FCM Device Tokens and Notifications tables
BEGIN;

CREATE TABLE IF NOT EXISTS device_tokens (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fcm_token           TEXT NOT NULL UNIQUE,
    platform            VARCHAR(50),
    device_name         VARCHAR(255),
    is_active           BOOLEAN DEFAULT TRUE,
    last_seen           TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_device_tokens_user_id ON device_tokens(user_id);


CREATE TABLE IF NOT EXISTS notifications (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title               VARCHAR(255) NOT NULL,
    body                TEXT NOT NULL,
    type                VARCHAR(100),
    reference_id        VARCHAR(255),
    image_url           TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- We're broadcasting admin notifications, so user_id is not required on the notification itself.
-- If user-specific notifications are needed in the future, a user_notifications join table should be used.

COMMIT;
