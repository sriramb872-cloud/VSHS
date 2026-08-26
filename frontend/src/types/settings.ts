// src/types/settings.ts
export interface SuperAdminSettings {
  id: number;
  platform_name: string;
  platform_logo?: string;
  default_language: string;
  time_zone: string;
  maintenance_mode: boolean;
  email_configuration?: Record<string, any>;
  backup_settings?: Record<string, any>;
}

export interface PrincipalSettings {
  id: number;
  school_name: string;
  school_logo?: string;
  school_address: string;
  phone_number: string;
  email: string;
  academic_year: string;
  school_working_days: string[];
  school_timings: string;
  grade_settings?: Record<string, any>;
  section_settings?: Record<string, any>;
}

export interface UserProfileSettings {
  id: number;
  profile_information: Record<string, any>;
  notification_preferences: Record<string, any>;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}