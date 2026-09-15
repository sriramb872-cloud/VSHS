import { getPetState } from './petStateMachine';

// Lightweight dependency-free unit checks. Run with any TypeScript test runner
// by importing this module; assertions intentionally cover precedence as well.
export function runPetStateMachineTests(): void {
  console.assert(getPetState('STUDENT', {}, { greeting: true }) === 'greeting');
  console.assert(getPetState('STUDENT', {}, { farewell: true, greeting: true }) === 'farewell');
  console.assert(getPetState('PRINCIPAL', { unreadAnnouncements: 1 }) === 'notify');
  console.assert(getPetState('STUDENT', { attendancePercentage: 60 }) === 'worried');
  console.assert(getPetState('STUDENT', { overdueHomework: 1 }) === 'worried');
  console.assert(getPetState('STUDENT', { attendancePercentage: 96 }) === 'happy');
  console.assert(getPetState('TEACHER', { pendingMarks: true }) === 'worried');
  console.assert(getPetState('PRINCIPAL') === 'idle');
}
