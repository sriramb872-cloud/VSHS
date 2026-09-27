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

/** Mirrors the backend `SuperAdminSettingsUpdate` schema (all fields optional). */
export type SuperAdminSettingsUpdate = Partial<Omit<SuperAdminSettings, 'id'>>;

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

/** Mirrors the backend `PrincipalSettingsUpdate` schema (all fields optional). */
export type PrincipalSettingsUpdate = Partial<Omit<PrincipalSettings, 'id'>>;

/** Mirrors the backend `UserProfileSettingsResponse` schema. */
export interface UserProfileSettings {
  id: number;
  profile_information: Record<string, any>;
  notification_preferences: Record<string, any>;
}

/**
 * Mirrors the backend `UserProfileSettingsBase` schema, which `PUT
 * /settings/user` accepts. Note it has no `id` - only the two payload blocks.
 */
export type UserProfileSettingsUpdate = Partial<
  Pick<UserProfileSettings, 'profile_information' | 'notification_preferences'>
>;

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}