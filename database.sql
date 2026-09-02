DROP DATABASE IF EXISTS vshs_db;
CREATE DATABASE vshs_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE vshs_db;

-- ==========================================================
-- 1. SCHOOLS
-- ==========================================================
CREATE TABLE schools (
    school_id INT AUTO_INCREMENT PRIMARY KEY,
    school_name VARCHAR(150) NOT NULL,
    school_code VARCHAR(30) UNIQUE NULL,
    email VARCHAR(100) NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_schools_code (school_code)
) ENGINE=InnoDB;

-- ==========================================================
-- 2. USERS & AUTHENTICATION
-- ==========================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NULL,
    mobile_number VARCHAR(15) NOT NULL,
    email VARCHAR(100) UNIQUE NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    profile_photo VARCHAR(255) NULL,
    role ENUM('SUPER_ADMIN', 'PRINCIPAL', 'TEACHER', 'STUDENT') NOT NULL,
    account_status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_users_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE SET NULL,
    INDEX idx_users_mobile (mobile_number),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

CREATE TABLE roles (
    role_id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ==========================================================
-- 3. ACADEMIC STRUCTURE
-- ==========================================================
CREATE TABLE academic_years (
    academic_year_id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    year_name VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_current BOOLEAN DEFAULT FALSE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_academic_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT uq_school_academic_year UNIQUE (school_id, year_name),
    INDEX idx_academic_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE grades (
    grade_id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    grade_name VARCHAR(50) NOT NULL,
    grade_order INT DEFAULT 0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_grade_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT uq_school_grade_name UNIQUE (school_id, grade_name),
    INDEX idx_grade_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE teachers (
    teacher_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    school_id INT NOT NULL,
    employee_id VARCHAR(100) NULL,
    department VARCHAR(100) NULL,
    qualification VARCHAR(100) NULL,
    joining_date DATE NULL,
    address VARCHAR(500) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_teacher_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_teacher_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_teacher_user (user_id),
    INDEX idx_teacher_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE sections (
    section_id INT AUTO_INCREMENT PRIMARY KEY,
    grade_id INT NOT NULL,
    section_name VARCHAR(10) NOT NULL,
    class_teacher_id BIGINT NULL,
    school_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_section_grade FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE CASCADE,
    CONSTRAINT fk_section_school FOREIGN KEY (school_id) REFERENCES schools(school_id),
    CONSTRAINT fk_section_teacher FOREIGN KEY (class_teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    CONSTRAINT uq_grade_section_name UNIQUE (grade_id, section_name),
    INDEX idx_section_grade (grade_id),
    INDEX idx_section_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE subjects (
    subject_id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    subject_code VARCHAR(30) NULL,
    is_optional BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_subject_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT uq_school_subject_name UNIQUE (school_id, subject_name),
    INDEX idx_subject_school (school_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 4. PROFILES & ENROLLMENTS
-- ==========================================================
CREATE TABLE principal_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    school_id INT NOT NULL,
    joining_date DATE NULL,
    qualification VARCHAR(255) NULL,
    experience_years INT DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_principal_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_principal_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_principal_user (user_id),
    INDEX idx_principal_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE students (
    student_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    school_id INT NOT NULL,
    admission_number VARCHAR(30) NULL,
    roll_number VARCHAR(50) NULL,
    admission_date DATE NULL,
    date_of_birth DATE NULL,
    gender VARCHAR(20) NULL,
    blood_group VARCHAR(10) NULL,
    father_name VARCHAR(100) NULL,
    father_mobile VARCHAR(15) NULL,
    mother_name VARCHAR(100) NULL,
    mother_mobile VARCHAR(15) NULL,
    guardian_mobile VARCHAR(15) NULL,
    address VARCHAR(500) NULL,
    student_status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_student_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    CONSTRAINT fk_student_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_student_user (user_id),
    INDEX idx_student_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE student_enrollments (
    enrollment_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    academic_year_id INT NOT NULL,
    section_id INT NOT NULL,
    roll_number VARCHAR(20) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_enroll_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_enroll_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_enroll_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT uq_academic_section_roll UNIQUE (academic_year_id, section_id, roll_number),
    INDEX idx_enroll_student (student_id),
    INDEX idx_enroll_academic (academic_year_id),
    INDEX idx_enroll_section (section_id)
) ENGINE=InnoDB;

CREATE TABLE grade_subjects (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    grade_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id BIGINT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_gs_grade FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE CASCADE,
    CONSTRAINT fk_gs_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_gs_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    CONSTRAINT uq_grade_subject UNIQUE (grade_id, subject_id),
    INDEX idx_gs_grade (grade_id),
    INDEX idx_gs_subject (subject_id),
    INDEX idx_gs_teacher (teacher_id)
) ENGINE=InnoDB;

CREATE TABLE teacher_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    teacher_id BIGINT NOT NULL,
    subject_id INT NOT NULL,
    grade_id INT NOT NULL,
    section_id INT NOT NULL,
    school_id INT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_ts_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    CONSTRAINT fk_ts_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_ts_grade FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE CASCADE,
    CONSTRAINT fk_ts_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_ts_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT uq_teacher_subject_grade_section_school UNIQUE (teacher_id, subject_id, grade_id, section_id, school_id),
    INDEX idx_teacher_assignments (teacher_id, school_id),
    INDEX idx_class_subject_assignment (grade_id, section_id, subject_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 5. ATTENDANCE & HOMEWORK
-- ==========================================================
CREATE TABLE attendance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    academic_year_id INT NOT NULL,
    section_id INT NOT NULL,
    student_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('PRESENT', 'ABSENT', 'LATE', 'EXCUSED') DEFAULT 'PRESENT' NOT NULL,
    remarks VARCHAR(255) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_att_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_att_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_attendance_date UNIQUE (student_id, attendance_date),
    INDEX idx_att_section_date (section_id, attendance_date)
) ENGINE=InnoDB;

CREATE TABLE homework (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    section_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id BIGINT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    assigned_date DATE NOT NULL,
    due_date DATE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_hw_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_hw_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_hw_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_hw_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    INDEX idx_hw_section (section_id),
    INDEX idx_hw_teacher (teacher_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 6. EXAMS, EXAM SUBJECTS & MARKS
-- ==========================================================
CREATE TABLE exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    academic_year_id INT NOT NULL,
    grade_id INT NOT NULL,
    section_id INT NOT NULL,
    name VARCHAR(255) NOT NULL,
    exam_type VARCHAR(100) NOT NULL,
    assessment_mode ENUM('FORMATIVE', 'SUMMATIVE') DEFAULT 'FORMATIVE' NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('SCHEDULED', 'MARKS_IN_PROGRESS', 'PUBLISHED') DEFAULT 'SCHEDULED' NOT NULL,
    created_by_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_exam_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_grade FOREIGN KEY (grade_id) REFERENCES grades(grade_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_exam_creator FOREIGN KEY (created_by_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_exam_school (school_id),
    INDEX idx_exam_academic (academic_year_id),
    INDEX idx_exam_grade (grade_id),
    INDEX idx_exam_section (section_id)
) ENGINE=InnoDB;

CREATE TABLE exam_subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id BIGINT NULL,
    maximum_marks FLOAT DEFAULT 100.0 NOT NULL,
    passing_marks FLOAT DEFAULT 35.0 NOT NULL,
    is_marks_submitted BOOLEAN DEFAULT FALSE NOT NULL,
    submitted_at DATETIME NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_es_exam FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    CONSTRAINT fk_es_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_es_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE SET NULL,
    CONSTRAINT uq_exam_subject UNIQUE (exam_id, subject_id),
    INDEX idx_es_exam (exam_id),
    INDEX idx_es_subject (subject_id),
    INDEX idx_es_teacher (teacher_id)
) ENGINE=InnoDB;

CREATE TABLE exam_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    student_id INT NOT NULL,
    subject_id INT NOT NULL,
    written_test FLOAT DEFAULT 0.0 NOT NULL,
    project FLOAT DEFAULT 0.0 NOT NULL,
    read_reflection FLOAT DEFAULT 0.0 NOT NULL,
    notebook FLOAT DEFAULT 0.0 NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_er_exam FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    CONSTRAINT fk_er_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_er_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT uq_exam_student_subject_result UNIQUE (exam_id, student_id, subject_id),
    INDEX idx_er_exam (exam_id),
    INDEX idx_er_student (student_id),
    INDEX idx_er_subject (subject_id)
) ENGINE=InnoDB;

CREATE TABLE marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_subject_id INT NOT NULL,
    student_id INT NOT NULL,
    school_id INT NOT NULL,
    marks_obtained FLOAT NOT NULL,
    max_marks FLOAT DEFAULT 100.0 NOT NULL,
    remarks VARCHAR(255) NULL,
    entered_by_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_marks_es FOREIGN KEY (exam_subject_id) REFERENCES exam_subjects(id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_entered_by FOREIGN KEY (entered_by_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT uq_exam_subject_student_marks UNIQUE (exam_subject_id, student_id),
    INDEX idx_marks_student_exam_subject (student_id, exam_subject_id),
    INDEX idx_marks_school_exam_subject (school_id, exam_subject_id)
) ENGINE=InnoDB;

CREATE TABLE report_cards (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    academic_year_id INT NOT NULL,
    term_name VARCHAR(100) NOT NULL,
    total_marks FLOAT DEFAULT 0.0 NOT NULL,
    percentage FLOAT DEFAULT 0.0 NOT NULL,
    grade_letter VARCHAR(10) NULL,
    remarks VARCHAR(500) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_rc_student FOREIGN KEY (student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_rc_academic_year FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT uq_student_term_report_card UNIQUE (student_id, academic_year_id, term_name),
    INDEX idx_rc_student (student_id),
    INDEX idx_rc_academic (academic_year_id)
) ENGINE=InnoDB;

-- ==========================================================
-- 7. NOTIFICATIONS, CALENDAR & TIMETABLE
-- ==========================================================
CREATE TABLE notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NULL,
    sender_user_id INT NULL,
    sender_role VARCHAR(50) NULL,
    notification_type VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    target_class_id INT NULL,
    target_student_id INT NULL,
    user_id INT NULL,
    category VARCHAR(50) NULL,
    is_read BOOLEAN DEFAULT FALSE NOT NULL,
    reference_id INT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_notif_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_sender FOREIGN KEY (sender_user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    CONSTRAINT fk_notif_section FOREIGN KEY (target_class_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_student FOREIGN KEY (target_student_id) REFERENCES students(student_id) ON DELETE CASCADE,
    CONSTRAINT fk_notif_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_notif_school (school_id),
    INDEX idx_notif_user (user_id),
    INDEX idx_notif_section (target_class_id)
) ENGINE=InnoDB;

CREATE TABLE announcements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    target_role VARCHAR(50) DEFAULT 'ALL' NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_ann_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_ann_school (school_id)
) ENGINE=InnoDB;

CREATE TABLE calendar_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NULL,
    event_type VARCHAR(50) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_cal_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    INDEX idx_cal_school (school_id),
    INDEX idx_cal_start_date (start_date)
) ENGINE=InnoDB;

CREATE TABLE timetables (
    id INT AUTO_INCREMENT PRIMARY KEY,
    school_id INT NOT NULL,
    academic_year_id INT NOT NULL,
    section_id INT NOT NULL,
    subject_id INT NOT NULL,
    teacher_id BIGINT NOT NULL,
    day_of_week VARCHAR(20) NOT NULL,
    period_number INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_tt_school FOREIGN KEY (school_id) REFERENCES schools(school_id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_academic FOREIGN KEY (academic_year_id) REFERENCES academic_years(academic_year_id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_section FOREIGN KEY (section_id) REFERENCES sections(section_id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_subject FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE,
    CONSTRAINT fk_tt_teacher FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id) ON DELETE CASCADE,
    CONSTRAINT uq_section_day_period UNIQUE (section_id, day_of_week, period_number),
    INDEX idx_tt_school (school_id),
    INDEX idx_tt_teacher (teacher_id),
    INDEX idx_tt_section (section_id)
) ENGINE=InnoDB;

CREATE TABLE audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,
    resource VARCHAR(100) NOT NULL,
    details TEXT NULL,
    ip_address VARCHAR(50) NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT fk_audit_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL,
    INDEX idx_audit_user (user_id)
) ENGINE=InnoDB;
