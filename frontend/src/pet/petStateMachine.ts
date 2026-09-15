export type PetState = 'farewell' | 'greeting' | 'notify' | 'worried' | 'happy' | 'idle';
export type PetRole = 'SUPER_ADMIN' | 'PRINCIPAL' | 'TEACHER' | 'STUDENT' | string;

export interface PetDashboardData {
  unreadAnnouncements?: number;
  attendancePercentage?: number;
  overdueHomework?: number;
  pendingMarks?: boolean;
}

export function getPetState(
  role: PetRole,
  data: PetDashboardData = {},
  transient: Pick<Partial<Record<'farewell' | 'greeting', boolean>>, 'farewell' | 'greeting'> = {},
): PetState {
  if (transient.farewell) return 'farewell';
  if (transient.greeting) return 'greeting';
  if ((data.unreadAnnouncements || 0) > 0) return 'notify';
  if (role === 'STUDENT') {
    if ((data.attendancePercentage ?? 100) < 75 || (data.overdueHomework || 0) > 0) return 'worried';
    if ((data.attendancePercentage ?? 0) >= 95) return 'happy';
  }
  if (role === 'TEACHER' && data.pendingMarks) return 'worried';
  return 'idle';
}
