DROP DATABASE IF EXISTS vshs_db;
CREATE DATABASE vshs_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vshs_db;

-- ==========================================================
-- 1. SCHOOLS
-- ==========================================================
CREATE TABLE schools (
    school_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_name VARCHAR(150) NOT NULL,
    school_code VARCHAR(30) NOT NULL UNIQUE,
    board ENUM('STATE', 'CBSE', 'ICSE', 'IB', 'OTHER') NOT NULL DEFAULT 'STATE',
    affiliation_number VARCHAR(50),
    email VARCHAR(100),
    phone VARCHAR(20),
    website VARCHAR(150),
    address_line1 VARCHAR(255),
    city VARCHAR(100),
    district VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    logo_url VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ==========================================================
-- 2. USERS & AUTHENTICATION
-- ==========================================================
CREATE TABLE users (
    user_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NULL, -- NULL for Super Admin / System Principal initially
    full_name VARCHAR(100) NOT NULL,
    mobile_number VARCHAR(15) NOT NULL UNIQUE,
    email VARCHAR(100) UNIQUE NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('SUPER_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT') NOT NULL,
    profile_photo VARCHAR(255) NULL,
    account_status ENUM('PENDING_VERIFICATION', 'ACTIVE', 'ON_LEAVE', 'INACTIVE', 'SUSPENDED') DEFAULT 'ACTIVE',
    mobile_verified BOOLEAN DEFAULT TRUE, -- Kept TRUE to bypass OTP for now
    is_profile_completed BOOLEAN DEFAULT FALSE,
    must_change_password BOOLEAN DEFAULT FALSE,
    last_login DATETIME NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_users_mobile (mobile_number),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- ==========================================================
-- 3. ACADEMIC STRUCTURE
-- ==========================================================
CREATE TABLE academic_years (
    academic_year_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    year_name VARCHAR(20) NOT NULL, -- e.g., '2026-2027'
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_academic_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE grades (
    grade_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    grade_name VARCHAR(30) NOT NULL, -- e.g., 'Class 8'
    grade_order INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_grade_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    UNIQUE(school_id, grade_name)
) ENGINE=InnoDB;

-- Teachers can assign themselves to sections here
CREATE TABLE sections (
    section_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    grade_id INT UNSIGNED NOT NULL,
    section_name VARCHAR(10) NOT NULL, -- e.g., 'A'
    class_teacher_id BIGINT UNSIGNED NULL, -- Linked to teachers table
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_section_grade FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE CASCADE,
    UNIQUE(grade_id, section_name)
) ENGINE=InnoDB;

CREATE TABLE subjects (
    subject_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(30),
    is_optional BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_subject_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    UNIQUE(school_id, subject_name)
) ENGINE=InnoDB;

-- ==========================================================
-- 4. PROFILE TABLES
-- ==========================================================
CREATE TABLE principal_profiles (
    principal_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    school_id INT UNSIGNED NOT NULL,
    employee_id VARCHAR(30) NULL,
    joining_date DATE NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_principal_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_principal_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE teachers (
    teacher_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    school_id INT UNSIGNED NOT NULL,
    employee_id VARCHAR(30) NULL, -- Nullable for minimal onboarding by Principal
    qualification VARCHAR(100) NULL,
    joining_date DATE NULL,
    address TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_teacher_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Add foreign key constraint for section class teacher after teachers table is created
ALTER TABLE sections 
ADD CONSTRAINT fk_section_teacher 
FOREIGN KEY (class_teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL;

CREATE TABLE students (
    student_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL UNIQUE,
    school_id INT UNSIGNED NOT NULL,
    admission_number VARCHAR(30) NULL, -- Minimal onboarding by Teacher
    roll_number VARCHAR(50) NULL,
    admission_date DATE NULL,
    gender ENUM('MALE', 'FEMALE', 'OTHER') NULL,
    date_of_birth DATE NULL,
    blood_group VARCHAR(5) NULL,
    father_name VARCHAR(100) NULL,
    father_mobile VARCHAR(15) NULL,
    mother_name VARCHAR(100) NULL,
    mother_mobile VARCHAR(15) NULL,
    guardian_mobile VARCHAR(15) NOT NULL,
    address TEXT NULL,
    student_status ENUM('ACTIVE', 'TRANSFERRED', 'PASSED_OUT', 'DROPPED') DEFAULT 'ACTIVE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_student_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Enrollment mapping (Student -> Section -> Academic Year)
CREATE TABLE student_enrollments (
    enrollment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT UNSIGNED NOT NULL,
    academic_year_id INT UNSIGNED NOT NULL,
    section_id INT UNSIGNED NOT NULL,
    roll_number VARCHAR(20) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_enroll_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_enroll_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_enroll_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    UNIQUE(academic_year_id, section_id, roll_number)
) ENGINE=InnoDB;

-- Subject Mapping to Teacher + Section
CREATE TABLE subject_assignments (
    subject_assignment_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    academic_year_id INT UNSIGNED NOT NULL,
    section_id INT UNSIGNED NOT NULL,
    subject_id INT UNSIGNED NOT NULL,
    teacher_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_sa_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_sa_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_sa_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_sa_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    UNIQUE (academic_year_id, section_id, subject_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 5. DAILY ATTENDANCE (Section Level)
-- ==========================================================
CREATE TABLE attendance (
    attendance_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    section_id INT UNSIGNED NOT NULL,
    academic_year_id INT UNSIGNED NOT NULL,
    attendance_date DATE NOT NULL,
    marked_by_teacher_id BIGINT UNSIGNED NOT NULL,
    remarks VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_att_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_teacher FOREIGN KEY (marked_by_teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    UNIQUE(section_id, attendance_date)
) ENGINE=InnoDB;

CREATE TABLE attendance_details (
    attendance_detail_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    attendance_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    attendance_status ENUM('PRESENT', 'ABSENT', 'LEAVE') NOT NULL DEFAULT 'PRESENT',
    remarks VARCHAR(255) NULL,
    CONSTRAINT fk_att_det_master FOREIGN KEY (attendance_id) REFERENCES attendance(attendance_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_det_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE(attendance_id, student_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 6. HOMEWORK & SLIP TESTS
-- ==========================================================
CREATE TABLE homework (
    homework_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    subject_assignment_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    assigned_date DATE NOT NULL,
    due_date DATE NOT NULL,
    created_by_teacher_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_hw_sa FOREIGN KEY (subject_assignment_id) REFERENCES subject_assignments(subject_assignment_id) ON DELETE CASCADE,
    CONSTRAINT fk_hw_teacher FOREIGN KEY (created_by_teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE slip_tests (
    slip_test_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    subject_assignment_id BIGINT UNSIGNED NOT NULL,
    title VARCHAR(100) NOT NULL,
    test_date DATE NOT NULL,
    maximum_marks DECIMAL(5,2) NOT NULL,
    created_by_teacher_id BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_st_sa FOREIGN KEY (subject_assignment_id) REFERENCES subject_assignments(subject_assignment_id) ON DELETE CASCADE,
    CONSTRAINT fk_st_teacher FOREIGN KEY (created_by_teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE slip_test_results (
    slip_test_result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    slip_test_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    marks_obtained DECIMAL(5,2) NOT NULL,
    attendance_status ENUM('PRESENT', 'ABSENT') DEFAULT 'PRESENT',
    CONSTRAINT fk_str_test FOREIGN KEY (slip_test_id) REFERENCES slip_tests(slip_test_id) ON DELETE CASCADE,
    CONSTRAINT fk_str_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    UNIQUE (slip_test_id, student_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 7. EXAMINATIONS (FA1-FA4, SA1-SA2)
-- ==========================================================
CREATE TABLE exam_types (
    exam_type_id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    exam_type_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255) NULL
) ENGINE=InnoDB;

INSERT INTO exam_types (exam_type_name, description) VALUES
('FA1', 'Formative Assessment 1'),
('FA2', 'Formative Assessment 2'),
('FA3', 'Formative Assessment 3'),
('FA4', 'Formative Assessment 4'),
('SA1', 'Summative Assessment 1'),
('SA2', 'Summative Assessment 2');

CREATE TABLE exams (
    exam_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    academic_year_id INT UNSIGNED NOT NULL,
    exam_type_id INT UNSIGNED NOT NULL,
    exam_name VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_published BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_exam_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_type FOREIGN KEY (exam_type_id) REFERENCES exam_types(exam_type_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE exam_subjects (
    exam_subject_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    exam_id BIGINT UNSIGNED NOT NULL,
    subject_assignment_id BIGINT UNSIGNED NOT NULL,
    exam_date DATE NULL,
    maximum_marks DECIMAL(5,2) NOT NULL DEFAULT 100.00,
    passing_marks DECIMAL(5,2) NOT NULL DEFAULT 35.00,
    CONSTRAINT fk_es_exam FOREIGN KEY (exam_id) REFERENCES exams(exam_id) ON DELETE CASCADE,
    CONSTRAINT fk_es_sa FOREIGN KEY (subject_assignment_id) REFERENCES subject_assignments(subject_assignment_id) ON DELETE CASCADE,
    UNIQUE(exam_id, subject_assignment_id)
) ENGINE=InnoDB;

CREATE TABLE exam_results (
    exam_result_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    exam_subject_id BIGINT UNSIGNED NOT NULL,
    student_id BIGINT UNSIGNED NOT NULL,
    marks_obtained DECIMAL(5,2) NOT NULL,
    attendance_status ENUM('PRESENT', 'ABSENT') DEFAULT 'PRESENT',
    entered_by_teacher_id BIGINT UNSIGNED NOT NULL,
    CONSTRAINT fk_er_es FOREIGN KEY (exam_subject_id) REFERENCES exam_subjects(exam_subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_er_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_er_teacher FOREIGN KEY (entered_by_teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    UNIQUE(exam_subject_id, student_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 8. REPORT CARDS
-- ==========================================================
CREATE TABLE report_cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id BIGINT UNSIGNED NOT NULL,
    academic_year_id INT UNSIGNED NOT NULL,
    term_name VARCHAR(100) NOT NULL,
    total_marks FLOAT NOT NULL DEFAULT 0.0,
    percentage FLOAT NOT NULL DEFAULT 0.0,
    grade_letter VARCHAR(10) NULL,
    remarks VARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_rc_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_rc_academic_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_term_report_card UNIQUE (student_id, academic_year_id, term_name),
    INDEX ix_report_cards_student_id (student_id),
    INDEX ix_report_cards_academic_year_id (academic_year_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 9. NOTIFICATIONS & OTP PLACEHOLDER
-- ==========================================================
CREATE TABLE notifications (
    notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('GENERAL', 'HOMEWORK', 'ATTENDANCE', 'EXAM', 'SLIP_TEST') NOT NULL,
    sender_user_id BIGINT UNSIGNED NOT NULL,
    target_role ENUM('ALL', 'TEACHER', 'STUDENT') DEFAULT 'ALL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notif_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_sender FOREIGN KEY (sender_user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE user_notifications (
    user_notification_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    notification_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at DATETIME NULL,
    CONSTRAINT fk_un_notif FOREIGN KEY (notification_id) REFERENCES notifications(notification_id) ON DELETE CASCADE,
    CONSTRAINT fk_un_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(notification_id, user_id)
) ENGINE=InnoDB;

-- Table preserved for future SMS activation
CREATE TABLE otp_verifications (
    otp_id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    mobile_number VARCHAR(15) NOT NULL,
    otp_code CHAR(6) NOT NULL,
    expires_at DATETIME NOT NULL,
    verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ==========================================================
-- 10. ACADEMIC CALENDAR EVENTS
-- ==========================================================
CREATE TABLE IF NOT EXISTS calendar_events (
    id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    school_id INT UNSIGNED NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    event_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_cal_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_cal_school (school_id),
    INDEX idx_cal_start_date (start_date)
) ENGINE=InnoDB;


