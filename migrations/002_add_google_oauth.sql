-- Migration 002: Add Google OAuth support
-- - Makes mot_de_passe_hash nullable (OAuth users have no local password)
-- - Adds google_id column for Google OAuth provider ID

ALTER TABLE utilisateur
    MODIFY COLUMN mot_de_passe_hash VARCHAR(255) NULL,
    ADD COLUMN google_id VARCHAR(255) NULL UNIQUE AFTER mot_de_passe_hash;
