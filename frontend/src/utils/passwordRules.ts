// src/utils/passwordRules.ts
//
// The client-side mirror of the server's password policy
// (`backend-python/app/services/password_reset.py::validate_password_strength`).
//
// It exists ONLY to give the user live feedback before they submit. The server
// is the authority: it re-checks everything and additionally rejects shipped
// defaults and the account's current password.

export interface PasswordRule {
  id: string;
  label: string;
  test: (value: string) => boolean;
}

/** 8+ characters, one uppercase, one lowercase, one digit. */
export const PASSWORD_RULES: PasswordRule[] = [
  { id: 'len', label: 'At least 8 characters', test: (value) => value.length >= 8 },
  { id: 'upper', label: 'An uppercase letter', test: (value) => /[A-Z]/.test(value) },
  { id: 'lower', label: 'A lowercase letter', test: (value) => /[a-z]/.test(value) },
  { id: 'digit', label: 'A number', test: (value) => /[0-9]/.test(value) },
];

/** Number of rules currently satisfied. */
export function passwordRulesPassed(value: string): number {
  return PASSWORD_RULES.filter((rule) => rule.test(value)).length;
}

/** `true` when every rule passes (submit-ready). */
export function passwordMeetsPolicy(value: string): boolean {
  return passwordRulesPassed(value) === PASSWORD_RULES.length;
}
