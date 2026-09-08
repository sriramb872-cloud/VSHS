-- MySQL dump 10.13  Distrib 8.4.9, for Win64 (x86_64)
--
-- Host: localhost    Database: vshs_db
-- ------------------------------------------------------
-- Server version	8.4.9

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `academic_years`
--

DROP TABLE IF EXISTS `academic_years`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `academic_years` (
  `academic_year_id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `year_name` varchar(20) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `is_current` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`academic_year_id`),
  UNIQUE KEY `uq_school_academic_year` (`school_id`,`year_name`),
  KEY `ix_academic_years_academic_year_id` (`academic_year_id`),
  KEY `ix_academic_years_school_id` (`school_id`),
  CONSTRAINT `academic_years_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `announcements`
--

DROP TABLE IF EXISTS `announcements`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `announcements` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `created_by` int DEFAULT NULL,
  `title` varchar(255) NOT NULL,
  `content` text NOT NULL,
  `target_role` varchar(50) DEFAULT NULL,
  `priority` varchar(50) DEFAULT NULL,
  `academic_year_id` int DEFAULT NULL,
  `grade_id` int DEFAULT NULL,
  `section_id` int DEFAULT NULL,
  `publish_date` datetime NOT NULL,
  `expiry_date` datetime DEFAULT NULL,
  `is_active` tinyint(1) NOT NULL,
  `status_value` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_announcements_school_id` (`school_id`),
  KEY `ix_announcements_created_by` (`created_by`),
  KEY `ix_announcements_id` (`id`),
  CONSTRAINT `announcements_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `announcements_ibfk_2` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `attendance_records`
--

DROP TABLE IF EXISTS `attendance_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `attendance_records` (
  `attendance_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `section_id` int NOT NULL,
  `date` date NOT NULL,
  `status` enum('PRESENT','ABSENT','LATE','LEAVE') NOT NULL,
  `recorded_by` int DEFAULT NULL,
  PRIMARY KEY (`attendance_id`),
  UNIQUE KEY `uq_student_attendance_date` (`student_id`,`date`),
  KEY `ix_attendance_records_attendance_id` (`attendance_id`),
  KEY `ix_attendance_records_section_id` (`section_id`),
  KEY `ix_attendance_records_student_id` (`student_id`),
  KEY `ix_attendance_records_date` (`date`),
  CONSTRAINT `attendance_records_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `attendance_records_ibfk_2` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `audit_logs`
--

DROP TABLE IF EXISTS `audit_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `audit_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `school_id` int DEFAULT NULL,
  `action` varchar(100) NOT NULL,
  `resource_type` varchar(100) NOT NULL,
  `resource_id` varchar(100) DEFAULT NULL,
  `details` json DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `timestamp` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `ix_audit_logs_timestamp` (`timestamp`),
  KEY `ix_audit_logs_user_id` (`user_id`),
  KEY `ix_audit_logs_resource_type` (`resource_type`),
  KEY `idx_audit_resource` (`resource_type`,`resource_id`),
  KEY `ix_audit_logs_id` (`id`),
  KEY `ix_audit_logs_action` (`action`),
  KEY `ix_audit_logs_school_id` (`school_id`),
  KEY `idx_audit_school_timestamp` (`school_id`,`timestamp`),
  CONSTRAINT `audit_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `audit_logs_ibfk_2` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `calendar_events`
--

DROP TABLE IF EXISTS `calendar_events`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `calendar_events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text,
  `event_type` varchar(50) NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_calendar_events_start_date` (`start_date`),
  KEY `ix_calendar_events_id` (`id`),
  KEY `ix_calendar_events_school_id` (`school_id`),
  CONSTRAINT `calendar_events_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exam_results`
--

DROP TABLE IF EXISTS `exam_results`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exam_results` (
  `id` int NOT NULL AUTO_INCREMENT,
  `exam_id` int NOT NULL,
  `student_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `written_test` float NOT NULL,
  `project` float NOT NULL,
  `read_reflection` float NOT NULL,
  `notebook` float NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_exam_student_subject_result` (`exam_id`,`student_id`,`subject_id`),
  KEY `ix_exam_results_subject_id` (`subject_id`),
  KEY `ix_exam_results_exam_id` (`exam_id`),
  KEY `ix_exam_results_student_id` (`student_id`),
  KEY `ix_exam_results_id` (`id`),
  CONSTRAINT `exam_results_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `exam_results_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `exam_results_ibfk_3` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exam_subjects`
--

DROP TABLE IF EXISTS `exam_subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exam_subjects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `exam_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `teacher_id` int DEFAULT NULL,
  `maximum_marks` float NOT NULL,
  `passing_marks` float NOT NULL,
  `is_marks_submitted` tinyint(1) NOT NULL,
  `submitted_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_exam_subject` (`exam_id`,`subject_id`),
  KEY `ix_exam_subjects_teacher_id` (`teacher_id`),
  KEY `ix_exam_subjects_exam_id` (`exam_id`),
  KEY `ix_exam_subjects_subject_id` (`subject_id`),
  KEY `ix_exam_subjects_id` (`id`),
  CONSTRAINT `exam_subjects_ibfk_1` FOREIGN KEY (`exam_id`) REFERENCES `exams` (`id`) ON DELETE CASCADE,
  CONSTRAINT `exam_subjects_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE,
  CONSTRAINT `exam_subjects_ibfk_3` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `exams`
--

DROP TABLE IF EXISTS `exams`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `exams` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `academic_year_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `section_id` int NOT NULL,
  `name` varchar(255) NOT NULL,
  `exam_type` varchar(100) NOT NULL,
  `assessment_mode` enum('FORMATIVE','SUMMATIVE') NOT NULL,
  `start_date` date NOT NULL,
  `end_date` date NOT NULL,
  `status` enum('SCHEDULED','MARKS_IN_PROGRESS','PUBLISHED') NOT NULL,
  `created_by_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `created_by_id` (`created_by_id`),
  KEY `ix_exams_id` (`id`),
  KEY `ix_exams_section_id` (`section_id`),
  KEY `ix_exams_grade_id` (`grade_id`),
  KEY `ix_exams_academic_year_id` (`academic_year_id`),
  KEY `ix_exams_school_id` (`school_id`),
  CONSTRAINT `exams_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `exams_ibfk_2` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`academic_year_id`) ON DELETE CASCADE,
  CONSTRAINT `exams_ibfk_3` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `exams_ibfk_4` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `exams_ibfk_5` FOREIGN KEY (`created_by_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `grade_subjects`
--

DROP TABLE IF EXISTS `grade_subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `grade_subjects` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `grade_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `teacher_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_grade_subject` (`grade_id`,`subject_id`),
  KEY `ix_grade_subjects_subject_id` (`subject_id`),
  KEY `ix_grade_subjects_teacher_id` (`teacher_id`),
  KEY `ix_grade_subjects_id` (`id`),
  KEY `ix_grade_subjects_grade_id` (`grade_id`),
  CONSTRAINT `grade_subjects_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `grade_subjects_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE,
  CONSTRAINT `grade_subjects_ibfk_3` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `grades`
--

DROP TABLE IF EXISTS `grades`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `grades` (
  `grade_id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `grade_name` varchar(30) NOT NULL,
  `grade_code` varchar(20) DEFAULT NULL,
  `description` varchar(255) DEFAULT NULL,
  `grade_order` int NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`grade_id`),
  UNIQUE KEY `uq_school_grade_name` (`school_id`,`grade_name`),
  KEY `ix_grades_school_id` (`school_id`),
  KEY `ix_grades_grade_id` (`grade_id`),
  CONSTRAINT `grades_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `homework`
--

DROP TABLE IF EXISTS `homework`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `homework` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `teacher_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `section_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text NOT NULL,
  `assigned_date` date NOT NULL,
  `due_date` date NOT NULL,
  `attachment_url` varchar(500) DEFAULT NULL,
  `is_published` tinyint(1) NOT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  KEY `ix_homework_teacher_id` (`teacher_id`),
  KEY `ix_homework_school_id` (`school_id`),
  KEY `ix_homework_id` (`id`),
  KEY `ix_homework_subject_id` (`subject_id`),
  KEY `ix_homework_section_id` (`section_id`),
  KEY `ix_homework_grade_id` (`grade_id`),
  CONSTRAINT `homework_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `homework_ibfk_2` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE CASCADE,
  CONSTRAINT `homework_ibfk_3` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `homework_ibfk_4` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `homework_ibfk_5` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `marks`
--

DROP TABLE IF EXISTS `marks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `marks` (
  `id` int NOT NULL AUTO_INCREMENT,
  `exam_subject_id` int NOT NULL,
  `student_id` int NOT NULL,
  `school_id` int NOT NULL,
  `marks_obtained` float NOT NULL,
  `max_marks` float NOT NULL,
  `remarks` varchar(255) DEFAULT NULL,
  `entered_by_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_exam_subject_student_marks` (`exam_subject_id`,`student_id`),
  KEY `entered_by_id` (`entered_by_id`),
  KEY `idx_marks_school_exam_subject` (`school_id`,`exam_subject_id`),
  KEY `ix_marks_id` (`id`),
  KEY `idx_marks_student_exam_subject` (`student_id`,`exam_subject_id`),
  KEY `ix_marks_school_id` (`school_id`),
  KEY `ix_marks_student_id` (`student_id`),
  KEY `ix_marks_exam_subject_id` (`exam_subject_id`),
  CONSTRAINT `marks_ibfk_1` FOREIGN KEY (`exam_subject_id`) REFERENCES `exam_subjects` (`id`) ON DELETE CASCADE,
  CONSTRAINT `marks_ibfk_2` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `marks_ibfk_3` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `marks_ibfk_4` FOREIGN KEY (`entered_by_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `chk_marks_obtained_positive` CHECK ((`marks_obtained` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `notifications`
--

DROP TABLE IF EXISTS `notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `notifications` (
  `notification_id` int NOT NULL AUTO_INCREMENT,
  `school_id` int DEFAULT NULL,
  `sender_user_id` int DEFAULT NULL,
  `sender_role` varchar(50) DEFAULT NULL,
  `notification_type` varchar(50) NOT NULL,
  `title` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `target_class_id` int DEFAULT NULL,
  `target_student_id` int DEFAULT NULL,
  `user_id` int DEFAULT NULL,
  `category` varchar(50) DEFAULT NULL,
  `is_read` tinyint(1) NOT NULL,
  `reference_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`notification_id`),
  KEY `ix_notifications_target_student_id` (`target_student_id`),
  KEY `ix_notifications_notification_id` (`notification_id`),
  KEY `ix_notifications_sender_user_id` (`sender_user_id`),
  KEY `ix_notifications_target_class_id` (`target_class_id`),
  KEY `ix_notifications_school_id` (`school_id`),
  KEY `ix_notifications_user_id` (`user_id`),
  CONSTRAINT `notifications_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_ibfk_2` FOREIGN KEY (`sender_user_id`) REFERENCES `users` (`user_id`) ON DELETE SET NULL,
  CONSTRAINT `notifications_ibfk_3` FOREIGN KEY (`target_class_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_ibfk_4` FOREIGN KEY (`target_student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `notifications_ibfk_5` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `principal_profiles`
--

DROP TABLE IF EXISTS `principal_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `principal_profiles` (
  `principal_id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `school_id` int NOT NULL,
  `employee_id` varchar(30) DEFAULT NULL,
  `joining_date` date DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`principal_id`),
  UNIQUE KEY `ix_principal_profiles_user_id` (`user_id`),
  KEY `ix_principal_profiles_school_id` (`school_id`),
  KEY `ix_principal_profiles_principal_id` (`principal_id`),
  CONSTRAINT `principal_profiles_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `principal_profiles_ibfk_2` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `report_cards`
--

DROP TABLE IF EXISTS `report_cards`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `report_cards` (
  `id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `academic_year_id` int NOT NULL,
  `term_name` varchar(100) NOT NULL,
  `total_marks` float NOT NULL,
  `percentage` float NOT NULL,
  `grade_letter` varchar(10) DEFAULT NULL,
  `remarks` varchar(500) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_student_term_report_card` (`student_id`,`academic_year_id`,`term_name`),
  KEY `ix_report_cards_academic_year_id` (`academic_year_id`),
  KEY `ix_report_cards_id` (`id`),
  KEY `ix_report_cards_student_id` (`student_id`),
  CONSTRAINT `report_cards_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `report_cards_ibfk_2` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`academic_year_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `roles`
--

DROP TABLE IF EXISTS `roles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `roles` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` enum('SUPER_ADMIN','PRINCIPAL','TEACHER','STUDENT') NOT NULL,
  `description` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_roles_name` (`name`),
  KEY `ix_roles_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `school_settings`
--

DROP TABLE IF EXISTS `school_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `school_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `school_name` varchar(255) DEFAULT NULL,
  `school_logo` varchar(500) DEFAULT NULL,
  `school_address` varchar(500) DEFAULT NULL,
  `phone_number` varchar(50) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `academic_year` varchar(50) DEFAULT NULL,
  `school_working_days` json DEFAULT NULL,
  `school_timings` varchar(100) DEFAULT NULL,
  `grade_settings` json DEFAULT NULL,
  `section_settings` json DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_school_settings_school_id` (`school_id`),
  CONSTRAINT `school_settings_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `schools`
--

DROP TABLE IF EXISTS `schools`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `schools` (
  `school_id` int NOT NULL AUTO_INCREMENT,
  `school_name` varchar(150) NOT NULL,
  `school_code` varchar(30) DEFAULT NULL,
  `email` varchar(100) DEFAULT NULL,
  `is_active` tinyint(1) DEFAULT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`school_id`),
  UNIQUE KEY `ix_schools_school_code` (`school_code`),
  KEY `ix_schools_school_id` (`school_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sections`
--

DROP TABLE IF EXISTS `sections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sections` (
  `section_id` int NOT NULL AUTO_INCREMENT,
  `grade_id` int NOT NULL,
  `section_name` varchar(10) NOT NULL,
  `class_teacher_id` int DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `school_id` int NOT NULL,
  PRIMARY KEY (`section_id`),
  UNIQUE KEY `uq_grade_section_name` (`grade_id`,`section_name`),
  KEY `class_teacher_id` (`class_teacher_id`),
  KEY `ix_sections_section_id` (`section_id`),
  KEY `ix_sections_school_id` (`school_id`),
  KEY `ix_sections_grade_id` (`grade_id`),
  CONSTRAINT `sections_ibfk_1` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `sections_ibfk_2` FOREIGN KEY (`class_teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE SET NULL,
  CONSTRAINT `sections_ibfk_3` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `student_enrollments`
--

DROP TABLE IF EXISTS `student_enrollments`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `student_enrollments` (
  `enrollment_id` int NOT NULL AUTO_INCREMENT,
  `student_id` int NOT NULL,
  `academic_year_id` int NOT NULL,
  `section_id` int NOT NULL,
  `roll_number` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`enrollment_id`),
  UNIQUE KEY `uq_academic_section_roll` (`academic_year_id`,`section_id`,`roll_number`),
  KEY `ix_student_enrollments_student_id` (`student_id`),
  KEY `ix_student_enrollments_academic_year_id` (`academic_year_id`),
  KEY `ix_student_enrollments_section_id` (`section_id`),
  KEY `ix_student_enrollments_enrollment_id` (`enrollment_id`),
  CONSTRAINT `student_enrollments_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`student_id`) ON DELETE CASCADE,
  CONSTRAINT `student_enrollments_ibfk_2` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`academic_year_id`) ON DELETE CASCADE,
  CONSTRAINT `student_enrollments_ibfk_3` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `students`
--

DROP TABLE IF EXISTS `students`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `students` (
  `student_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `school_id` int NOT NULL,
  `admission_number` varchar(30) DEFAULT NULL,
  `roll_number` varchar(50) DEFAULT NULL,
  `admission_date` date DEFAULT NULL,
  `date_of_birth` date DEFAULT NULL,
  `gender` varchar(20) DEFAULT NULL,
  `blood_group` varchar(10) DEFAULT NULL,
  `father_name` varchar(100) DEFAULT NULL,
  `father_mobile` varchar(15) DEFAULT NULL,
  `mother_name` varchar(100) DEFAULT NULL,
  `mother_mobile` varchar(15) DEFAULT NULL,
  `guardian_mobile` varchar(15) DEFAULT NULL,
  `address` varchar(500) DEFAULT NULL,
  `student_status` varchar(20) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`student_id`),
  UNIQUE KEY `ix_students_user_id` (`user_id`),
  KEY `ix_students_student_id` (`student_id`),
  KEY `ix_students_school_id` (`school_id`),
  CONSTRAINT `students_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `students_ibfk_2` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `subjects`
--

DROP TABLE IF EXISTS `subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `subjects` (
  `subject_id` int NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `subject_name` varchar(100) NOT NULL,
  `subject_code` varchar(30) DEFAULT NULL,
  `is_elective` tinyint(1) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`subject_id`),
  UNIQUE KEY `uq_school_subject_name` (`school_id`,`subject_name`),
  KEY `ix_subjects_subject_id` (`subject_id`),
  KEY `ix_subjects_school_id` (`school_id`),
  CONSTRAINT `subjects_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_settings`
--

DROP TABLE IF EXISTS `system_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_settings` (
  `id` int NOT NULL,
  `platform_name` varchar(255) NOT NULL,
  `platform_logo` varchar(500) DEFAULT NULL,
  `default_language` varchar(10) NOT NULL,
  `time_zone` varchar(50) NOT NULL,
  `maintenance_mode` tinyint(1) NOT NULL,
  `email_configuration` json DEFAULT NULL,
  `backup_settings` json DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `teacher_subjects`
--

DROP TABLE IF EXISTS `teacher_subjects`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teacher_subjects` (
  `id` int NOT NULL AUTO_INCREMENT,
  `teacher_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `section_id` int NOT NULL,
  `school_id` int NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_teacher_subject_grade_section_school` (`teacher_id`,`subject_id`,`grade_id`,`section_id`,`school_id`),
  KEY `ix_teacher_subjects_section_id` (`section_id`),
  KEY `ix_teacher_subjects_grade_id` (`grade_id`),
  KEY `ix_teacher_subjects_subject_id` (`subject_id`),
  KEY `idx_teacher_assignments` (`teacher_id`,`school_id`),
  KEY `ix_teacher_subjects_teacher_id` (`teacher_id`),
  KEY `idx_class_subject_assignment` (`grade_id`,`section_id`,`subject_id`),
  KEY `ix_teacher_subjects_school_id` (`school_id`),
  KEY `ix_teacher_subjects_id` (`id`),
  CONSTRAINT `teacher_subjects_ibfk_1` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE CASCADE,
  CONSTRAINT `teacher_subjects_ibfk_2` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE,
  CONSTRAINT `teacher_subjects_ibfk_3` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `teacher_subjects_ibfk_4` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `teacher_subjects_ibfk_5` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `teachers`
--

DROP TABLE IF EXISTS `teachers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `teachers` (
  `teacher_id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `school_id` int NOT NULL,
  `employee_id` varchar(100) DEFAULT NULL,
  `department` varchar(100) DEFAULT NULL,
  `qualification` varchar(100) DEFAULT NULL,
  `joining_date` date DEFAULT NULL,
  `address` varchar(500) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`teacher_id`),
  UNIQUE KEY `ix_teachers_user_id` (`user_id`),
  KEY `ix_teachers_teacher_id` (`teacher_id`),
  KEY `ix_teachers_school_id` (`school_id`),
  CONSTRAINT `teachers_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE,
  CONSTRAINT `teachers_ibfk_2` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `timetables`
--

DROP TABLE IF EXISTS `timetables`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `timetables` (
  `timetable_id` bigint NOT NULL AUTO_INCREMENT,
  `school_id` int NOT NULL,
  `academic_year_id` int NOT NULL,
  `grade_id` int NOT NULL,
  `section_id` int NOT NULL,
  `subject_id` int NOT NULL,
  `teacher_id` int NOT NULL,
  `day_of_week` varchar(20) NOT NULL,
  `start_time` time NOT NULL,
  `end_time` time NOT NULL,
  `room_number` varchar(30) DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`timetable_id`),
  KEY `ix_timetables_teacher_id` (`teacher_id`),
  KEY `ix_timetables_timetable_id` (`timetable_id`),
  KEY `ix_timetables_section_id` (`section_id`),
  KEY `ix_timetables_academic_year_id` (`academic_year_id`),
  KEY `ix_timetables_grade_id` (`grade_id`),
  KEY `ix_timetables_subject_id` (`subject_id`),
  KEY `ix_timetables_school_id` (`school_id`),
  CONSTRAINT `timetables_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_2` FOREIGN KEY (`academic_year_id`) REFERENCES `academic_years` (`academic_year_id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_3` FOREIGN KEY (`grade_id`) REFERENCES `grades` (`grade_id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_4` FOREIGN KEY (`section_id`) REFERENCES `sections` (`section_id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_5` FOREIGN KEY (`subject_id`) REFERENCES `subjects` (`subject_id`) ON DELETE CASCADE,
  CONSTRAINT `timetables_ibfk_6` FOREIGN KEY (`teacher_id`) REFERENCES `teachers` (`teacher_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_app_settings`
--

DROP TABLE IF EXISTS `user_app_settings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_app_settings` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `profile_information` json DEFAULT NULL,
  `notification_preferences` json DEFAULT NULL,
  `created_at` datetime NOT NULL,
  `updated_at` datetime NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_user_app_settings_user_id` (`user_id`),
  CONSTRAINT `user_app_settings_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_notifications`
--

DROP TABLE IF EXISTS `user_notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_notifications` (
  `user_notification_id` bigint NOT NULL AUTO_INCREMENT,
  `notification_id` int NOT NULL,
  `user_id` int NOT NULL,
  `is_read` tinyint(1) DEFAULT NULL,
  `read_at` datetime DEFAULT NULL,
  PRIMARY KEY (`user_notification_id`),
  KEY `ix_user_notifications_user_id` (`user_id`),
  KEY `ix_user_notifications_notification_id` (`notification_id`),
  KEY `ix_user_notifications_user_notification_id` (`user_notification_id`),
  CONSTRAINT `user_notifications_ibfk_1` FOREIGN KEY (`notification_id`) REFERENCES `notifications` (`notification_id`) ON DELETE CASCADE,
  CONSTRAINT `user_notifications_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `school_id` int DEFAULT NULL,
  `mobile_number` varchar(15) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `password_hash` varchar(255) NOT NULL,
  `full_name` varchar(100) NOT NULL,
  `profile_photo` varchar(255) DEFAULT NULL,
  `role` enum('SUPER_ADMIN','PRINCIPAL','TEACHER','STUDENT') NOT NULL,
  `account_status` varchar(50) NOT NULL,
  `created_at` datetime DEFAULT NULL,
  `updated_at` datetime DEFAULT NULL,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `ix_users_email` (`email`),
  KEY `ix_users_school_id` (`school_id`),
  KEY `ix_users_role` (`role`),
  KEY `ix_users_user_id` (`user_id`),
  KEY `ix_users_mobile_number` (`mobile_number`),
  CONSTRAINT `users_ibfk_1` FOREIGN KEY (`school_id`) REFERENCES `schools` (`school_id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-09-08  0:32:59
