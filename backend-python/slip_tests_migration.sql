-- =============================================================================
-- SCHOLARIS — Slip Tests
-- Target database: vshs_db  (MySQL 8.x, InnoDB, utf8mb4)
--
-- STANDALONE + RE-RUNNABLE. Safe to run any number of times:
--   * the table is created with CREATE TABLE IF NOT EXISTS
--   * every index and foreign key is declared INSIDE the CREATE TABLE, so a
--     second run is a no-op instead of failing on "Duplicate key name"
--     (MySQL has no `CREATE INDEX IF NOT EXISTS`, which is exactly why the
--     indexes are inlined here).
--   * no other table is touched: this script only ever CREATEs slip_tests.
--
-- Mirrors backend-python/alembic/versions/0004_slip_tests.py, which the deploy
-- pipeline (`alembic upgrade head` in start.sh) applies automatically. Running
-- this file by hand is only needed when you apply schema changes manually.
--
-- TIMEZONE POLICY: `scheduled_date` and `start_time` are plain school-local
-- values. They are never converted to/from UTC anywhere in the feature — a
-- date typed as 2026-11-02 is stored and read back as 2026-11-02. The
-- timestamp columns follow the project-wide convention of naive UTC
-- (`datetime.utcnow`), see app/core/time_utils.py.
--
-- FUTURE WORK (deliberately NOT built here): per-student obtained marks. A
-- future `slip_test_results` table will link to `slip_tests.id` (one row per
-- student) and reuse `slip_tests.max_marks` as the denominator. Nothing in
-- this schema blocks that - `id` is a stable surrogate key and is indexed as
-- the primary key.
-- =============================================================================

CREATE TABLE IF NOT EXISTS `slip_tests` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `academic_year_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `section_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `teacher_id` int NOT NULL,
  `title` varchar(150) NOT NULL,
  `description` text DEFAULT NULL,
  `scheduled_date` date NOT NULL,
  `start_time` time DEFAULT NULL,
  `duration_minutes` int DEFAULT NULL,
  `max_marks` int NOT NULL,
  `status` enum('scheduled','cancelled','completed') NOT NULL DEFAULT 'scheduled',
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  -- Single-column indexes: one per `index=True` column on the SQLAlchemy
  -- model. They are declared explicitly (rather than left to MySQL's automatic
  -- FK indexes) so the names match `Base.metadata` exactly and `alembic check`
  -- reports no drift.
  KEY `ix_slip_tests_id` (`id`),
  KEY `ix_slip_tests_school_id` (`school_id`),
  KEY `ix_slip_tests_academic_year_id` (`academic_year_id`),
  KEY `ix_slip_tests_grade_id` (`grade_id`),
  KEY `ix_slip_tests_section_id` (`section_id`),
  KEY `ix_slip_tests_subject_id` (`subject_id`),
  KEY `ix_slip_tests_teacher_id` (`teacher_id`),
  KEY `ix_slip_tests_status` (`status`),
  -- Composite indexes required by the feature spec.
  -- Class listing for the student portal + teacher "count upcoming" cards.
  KEY `ix_slip_tests_school_year_class_date` (
    `school_id`, `academic_year_id`, `grade_id`, `section_id`, `scheduled_date`
  ),
  -- "Which classes does this teacher teach" + per-teacher date scans.
  KEY `ix_slip_tests_teacher_date` (`teacher_id`, `scheduled_date`),
  -- Defense in depth. The API validates max_marks > 0 and duration > 0 first,
  -- so a CHECK violation should be unreachable; it exists so a bad direct
  -- INSERT cannot create an unusable row.
  CONSTRAINT `ck_slip_tests_max_marks` CHECK (`max_marks` > 0),
  CONSTRAINT `ck_slip_tests_duration` CHECK (
    `duration_minutes` IS NULL OR `duration_minutes` > 0
  ),
  CONSTRAINT `slip_tests_ibfk_1` FOREIGN KEY (`school_id`)
    REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `slip_tests_ibfk_2` FOREIGN KEY (`academic_year_id`)
    REFERENCES `academic_years` (`academic_year_id`) ON DELETE CASCADE,
  CONSTRAINT `slip_tests_ibfk_3` FOREIGN KEY (`grade_id`)
    REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `slip_tests_ibfk_4` FOREIGN KEY (`section_id`)
    REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `slip_tests_ibfk_5` FOREIGN KEY (`subject_id`)
    REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE,
  CONSTRAINT `slip_tests_ibfk_6` FOREIGN KEY (`teacher_id`)
    REFERENCES `teachers` (`teacher_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- -----------------------------------------------------------------------------
-- Verification (read-only, safe to run): expect slip_tests with the two indexes
-- named above.
-- -----------------------------------------------------------------------------
-- SHOW CREATE TABLE slip_tests;