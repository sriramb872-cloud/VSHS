-- =============================================================================
-- SCHOLARIS — Password reset (OTP self-service + admin-assisted queue)
-- Target database: vshs_db  (MySQL 8.x, InnoDB, utf8mb4)
--
-- STANDALONE + RE-RUNNABLE. Safe to run any number of times:
--   * both tables are created with CREATE TABLE IF NOT EXISTS, with every
--     index and foreign key declared INSIDE the CREATE TABLE, so a second run
--     is a no-op instead of failing on "Duplicate key name" (MySQL has no
--     `CREATE INDEX IF NOT EXISTS`);
--   * the `users.must_change_password` add checks information_schema first
--     and does nothing when the column already exists;
--   * nothing existing is dropped or altered otherwise.
--
-- Mirrors backend-python/alembic/versions/0005_password_reset.py, which the
-- deploy pipeline (`alembic upgrade head` in start.sh) applies automatically.
-- Running this file by hand is only needed when you apply schema changes
-- manually. Run EITHER this file OR `alembic upgrade head` - never both.
--
-- WHAT IT ADDS
--   password_reset_otps       one row per requested 6-digit code. Stores an
--                             HMAC-SHA256 of the code (never the code), the
--                             expiry, the wrong-attempt counter, the source IP,
--                             and after verification the SHA-256 hash of the
--                             single-use reset token.
--   password_reset_requests   the staff work queue for accounts with no email
--                             (mainly students): pending/completed/rejected,
--                             who handled it and when.
--   users.must_change_password forces a first login to pick a new password
--                             after an admin-issued temporary password.
--
-- TIMEZONE POLICY: every timestamp column is naive UTC (`datetime.utcnow`
-- house style), see app/core/time_utils.py.
-- =============================================================================

CREATE TABLE IF NOT EXISTS `password_reset_otps` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `otp_hash` varchar(128) NOT NULL,
  `expires_at` datetime NOT NULL,
  `attempts` int NOT NULL DEFAULT '0',
  `used_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `request_ip` varchar(45) DEFAULT NULL,
  `reset_token_hash` varchar(64) DEFAULT NULL,
  `reset_token_expires_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  -- One per `index=True` column on the SQLAlchemy model, named exactly as
  -- `Base.metadata` names them so `alembic check` reports no drift.
  KEY `ix_password_reset_otps_id` (`id`),
  KEY `ix_password_reset_otps_user_id` (`user_id`),
  KEY `ix_password_reset_otps_reset_token_hash` (`reset_token_hash`),
  CONSTRAINT `password_reset_otps_ibfk_1` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS `password_reset_requests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `status` enum('pending','completed','rejected') NOT NULL DEFAULT 'pending',
  `requested_at` datetime NOT NULL,
  `handled_by` int DEFAULT NULL,
  `handled_at` datetime DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_password_reset_requests_id` (`id`),
  KEY `ix_password_reset_requests_user_id` (`user_id`),
  KEY `ix_password_reset_requests_status` (`status`),
  -- Required by the `handled_by` FK below. Declared explicitly (rather than
  -- left to MySQL) so it gets the same name the alembic-built schema has,
  -- instead of MySQL inventing one from the constraint name.
  KEY `handled_by` (`handled_by`),
  -- `user_id` CASCADE: deleting the account removes its queue entry.
  -- `handled_by` SET NULL: deleting the admin must not delete the record.
  CONSTRAINT `password_reset_requests_ibfk_1` FOREIGN KEY (`user_id`)
    REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `password_reset_requests_ibfk_2` FOREIGN KEY (`handled_by`)
    REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- -----------------------------------------------------------------------------
-- users.must_change_password - already present on databases created by 0001,
-- added here only when missing so a hand-managed `vshs_db` cannot be left
-- behind. The information_schema probe keeps the statement a no-op on re-run.
-- -----------------------------------------------------------------------------
SET @col_exists := (
  SELECT COUNT(*)
  FROM INFORMATION_SCHEMA.COLUMNS
  WHERE TABLE_SCHEMA = DATABASE()
    AND TABLE_NAME = 'users'
    AND COLUMN_NAME = 'must_change_password'
);
SET @ddl := IF(
  @col_exists = 0,
  'ALTER TABLE `users` ADD COLUMN `must_change_password` tinyint(1) NOT NULL DEFAULT 0',
  'SELECT 1'
);
PREPARE stmt FROM @ddl;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- -----------------------------------------------------------------------------
-- Verification (read-only, safe to run): expect both tables with the indexes
-- named above, and users.must_change_password present exactly once.
-- -----------------------------------------------------------------------------
-- SHOW CREATE TABLE password_reset_otps;
-- SHOW CREATE TABLE password_reset_requests;
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
--   WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users'
--     AND COLUMN_NAME = 'must_change_password';
