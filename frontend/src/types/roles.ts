// src/types/roles.ts
import { UserRole } from './index';

/** Mirrors the backend role schemas (app/schemas/role.py). */
export interface RoleSummary {
  name: string;
  description: string;
  is_assignable: boolean;
  user_count: number;
  active_user_count: number;
}

export interface RoleListResponse {
  total: number;
  items: RoleSummary[];
}

export interface RoleAssignmentResult {
  user: {
    id: number;
    school_id: number | null;
    school_name?: string | null;
    mobile: string;
    email?: string | null;
    display_name: string;
    /** A `UserRole` member; the backend assigns `UserRole(target_role)`. */
    role: UserRole;
    is_active: string;
  };
  message: string;
}
