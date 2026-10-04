// frontend/src/pages/auth/ForgotPassword.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowLeft,
  Check,
  CircleCheck,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
  Mail,
  ShieldAlert,
  Timer,
} from 'lucide-react';
import {
  ADMIN_HELP_MESSAGE,
  passwordResetService,
  toResetError,
  type ResetError,
} from '../../services/passwordReset';
import { PASSWORD_RULES, passwordRulesPassed } from '../../utils/passwordRules';

type Step = 'loginId' | 'otp' | 'password' | 'done';

/** Seconds the user must wait before asking for another code. */
const RESEND_SECONDS = 60;

const inputClass =
  'w-full h-12 pl-10 pr-4 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all';

const labelClass =
  'block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5';

export const ForgotPassword: React.FC = () => {
  const [step, setStep] = useState<Step>('loginId');

  const [loginId, setLoginId] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const [error, setError] = useState<ResetError | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // The reset token lives only in this component's memory: never persisted.
  const resetTokenRef = useRef<string | null>(null);
  const [resendIn, setResendIn] = useState(0);
  const [resendNotice, setResendNotice] = useState(false);

  const otpInputRef = useRef<HTMLInputElement>(null);

  /* --- resend countdown ------------------------------------------------- */
  useEffect(() => {
    if (resendIn <= 0) return;
    const timer = window.setInterval(() => {
      setResendIn((value) => (value <= 1 ? 0 : value - 1));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendIn]);

  const startCountdown = useCallback(() => setResendIn(RESEND_SECONDS), []);

  const clearError = () => setError(null);

  const goToLogin = () => {
    resetTokenRef.current = null;
    setStep('loginId');
    setOtp('');
    setNewPassword('');
    setConfirmPassword('');
    setNotice(null);
    setResendNotice(false);
    setError(null);
  };

  /* --- step 1: ask for a code ------------------------------------------ */
  const handleLoginIdSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();
    setNotice(null);
    setLoading(true);
    try {
      const data = await passwordResetService.forgotPassword(loginId.trim());
      // Same text for every input - showing it is the whole point.
      setNotice(data.message || 'If an account exists, a code has been sent.');
      setStep('otp');
      setOtp('');
      startCountdown();
      window.setTimeout(() => otpInputRef.current?.focus(), 100);
    } catch (err) {
      setError(toResetError(err, 'Could not send the code right now. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendIn > 0 || loading) return;
    clearError();
    setResendNotice(false);
    setLoading(true);
    try {
      const data = await passwordResetService.forgotPassword(loginId.trim());
      setNotice(data.message || 'If an account exists, a code has been sent.');
      setOtp('');
      setResendNotice(true);
      startCountdown();
      otpInputRef.current?.focus();
    } catch (err) {
      setError(toResetError(err, 'Could not send a new code right now. Please try again.'));
    } finally {
      setLoading(false);
    }
  };

  /* --- step 2: verify the code ------------------------------------------ */
  const handleOtpSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const presented = otp.replace(/\s/g, '');
    if (presented.length !== 6) {
      setError({ message: 'Enter the 6-digit code from your email.', code: null, status: 0, offline: false });
      return;
    }
    clearError();
    setLoading(true);
    try {
      const data = await passwordResetService.verifyOtp(loginId.trim(), presented);
      resetTokenRef.current = data.reset_token;
      setStep('password');
      setNewPassword('');
      setConfirmPassword('');
      setShowPassword(false);
    } catch (err) {
      const failure = toResetError(err, 'That code could not be verified. Please try again.');
      setError(failure);
      // Codes expire, lock out or hand over to admin help - the user needs a
      // fresh one in every one of those cases.
      if (failure.code === 'OTP_EXPIRED' || failure.code === 'OTP_LOCKED') {
        setOtp('');
        setResendIn(0);
      }
    } finally {
      setLoading(false);
    }
  };

  /* --- step 3: set the new password ------------------------------------- */
  const rulesPassed = passwordRulesPassed(newPassword);
  const passwordMatches = newPassword.length > 0 && newPassword === confirmPassword;

  const handlePasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearError();

    if (!resetTokenRef.current) {
      setError({
        message: 'This reset has expired. Please start again.',
        code: 'RESET_TOKEN_INVALID',
        status: 0,
        offline: false,
      });
      return;
    }
    if (rulesPassed !== PASSWORD_RULES.length) {
      setError({
        message: 'Your password does not meet the requirements yet.',
        code: 'WEAK_PASSWORD',
        status: 0,
        offline: false,
      });
      return;
    }
    if (newPassword !== confirmPassword) {
      setError({
        message: 'New password and confirmation do not match.',
        code: null,
        status: 0,
        offline: false,
      });
      return;
    }

    setLoading(true);
    try {
      await passwordResetService.resetPassword(resetTokenRef.current, newPassword);
      resetTokenRef.current = null;
      setStep('done');
    } catch (err) {
      const failure = toResetError(err, 'Could not reset the password. Please try again.');
      setError(failure);
      if (failure.code === 'RESET_TOKEN_INVALID') {
        // Token spent/expired: only a brand-new request can continue.
        resetTokenRef.current = null;
      }
    } finally {
      setLoading(false);
    }
  };

  /* --- shared bits ------------------------------------------------------- */
  const banner = (kind: 'error' | 'info', text: string) => (
    <div
      className={`mb-5 flex items-start gap-2.5 p-3.5 rounded-xl text-xs sm:text-sm animate-in fade-in duration-150 ${
        kind === 'error'
          ? 'bg-rose-50 border border-rose-200 text-rose-700'
          : 'bg-amber-50 border border-amber-200 text-amber-800'
      }`}
    >
      {kind === 'error' ? (
        <ShieldAlert className="w-4 h-4 mt-0.5 flex-shrink-0 text-rose-600" />
      ) : (
        <Mail className="w-4 h-4 mt-0.5 flex-shrink-0 text-amber-600" />
      )}
      <span className="font-medium leading-snug">{text}</span>
    </div>
  );

  const spinner = (label: string) => (
    <>
      <Loader2 className="w-4.5 h-4.5 animate-spin" />
      <span>{label}</span>
    </>
  );

  /* ======================== STEP 1: login ID ============================= */
  if (step === 'loginId') {
    return (
      <div className="w-full">
        <div className="text-center mb-6">
          <div className="w-11 h-11 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-3">
            <KeyRound className="w-5.5 h-5.5 text-indigo-600" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Forgot Password
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Enter your login ID and we&rsquo;ll email you a 6-digit code.
          </p>
        </div>

        {error && banner('error', error.message)}
        {notice && banner('info', notice)}

        <form className="space-y-4" onSubmit={handleLoginIdSubmit}>
          <div>
            <label htmlFor="forgot-login-id" className={labelClass}>
              Login ID
            </label>
            <p className="mb-1.5 text-xs text-slate-500">
              Mobile number, email address, student ID, or employee ID.
            </p>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="forgot-login-id"
                name="login_id"
                type="text"
                required
                autoComplete="username"
                value={loginId}
                onChange={(e) => setLoginId(e.target.value)}
                placeholder="e.g. 9876543210, name@school.edu, SCH2026001"
                className={inputClass}
              />
            </div>
          </div>

          <button
            id="forgot-send-code-btn"
            type="submit"
            disabled={loading || !loginId.trim()}
            className="w-full h-12 mt-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          >
            {loading ? spinner('Sending…') : <span>Send Reset Code</span>}
          </button>
        </form>

        <div className="text-center pt-4">
          <Link
            to="/login"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Back to Sign In</span>
          </Link>
        </div>
      </div>
    );
  }

  /* ======================== STEP 2: enter the code ======================= */
  if (step === 'otp') {
    const adminHelp = error?.code === 'ADMIN_RESET_REQUIRED';
    return (
      <div className="w-full">
        <div className="text-center mb-6">
          <div className="w-11 h-11 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-3">
            <Mail className="w-5.5 h-5.5 text-indigo-600" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Enter Code
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            If an account exists for{' '}
            <span className="font-semibold text-slate-700">{loginId}</span>, a 6-digit code was
            sent to its email. It expires in 10 minutes.
          </p>
        </div>

        {/* One banner only: the standing generic notice, or the resend update. */}
        {banner('info', resendNotice ? 'A new code has been sent.' : notice || 'If an account exists, a code has been sent.')}
        {/* The admin-help card below already says it, so the error banner would only duplicate it. */}
        {error && !adminHelp && banner('error', error.message)}

        {adminHelp ? (
          <div className="space-y-4">
            <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 text-xs sm:text-sm text-slate-600 leading-relaxed">
              {ADMIN_HELP_MESSAGE}
            </div>
            <button
              type="button"
              onClick={goToLogin}
              className="w-full h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md transition-all"
            >
              Back to Sign In
            </button>
          </div>
        ) : (
          <form className="space-y-4" onSubmit={handleOtpSubmit}>
            <div>
              <label htmlFor="forgot-otp" className={labelClass}>
                6-Digit Code
              </label>
              <div className="relative">
                <KeyRound className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <input
                  ref={otpInputRef}
                  id="forgot-otp"
                  name="otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  maxLength={6}
                  required
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  // Centered + wide letter-spacing so a 6-digit code reads as
                  // six boxes on a phone without needing six inputs.
                  className="w-full h-12 px-4 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 placeholder-slate-300 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all text-center text-lg font-bold"
                  style={{ letterSpacing: '0.5em' }}
                />
              </div>
            </div>

            <button
              id="forgot-verify-otp-btn"
              type="submit"
              disabled={loading || otp.length !== 6}
              className="w-full h-12 mt-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
            >
              {loading ? spinner('Verifying…') : <span>Verify Code</span>}
            </button>

            <div className="flex items-center justify-between pt-1">
              <button
                type="button"
                onClick={goToLogin}
                className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
                <span>Use a different ID</span>
              </button>

              {resendIn > 0 ? (
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-400">
                  <Timer className="w-3.5 h-3.5" />
                  <span>Resend in {resendIn}s</span>
                </span>
              ) : (
                <button
                  id="forgot-resend-btn"
                  type="button"
                  onClick={handleResend}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-indigo-600 hover:text-indigo-700 disabled:opacity-60"
                >
                  Resend code
                </button>
              )}
            </div>
          </form>
        )}
      </div>
    );
  }

  /* ======================== STEP 3: new password ========================= */
  if (step === 'password') {
    return (
      <div className="w-full">
        <div className="text-center mb-6">
          <div className="w-11 h-11 rounded-2xl bg-indigo-50 border border-indigo-100 flex items-center justify-center mx-auto mb-3">
            <Lock className="w-5.5 h-5.5 text-indigo-600" />
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Set New Password
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Choose a password you haven&rsquo;t used here before.
          </p>
        </div>

        {error && banner('error', error.message)}

        <form className="space-y-4" onSubmit={handlePasswordSubmit}>
          <div>
            <label htmlFor="forgot-new-password" className={labelClass}>
              New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="forgot-new-password"
                name="new_password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                className={`${inputClass} pr-11`}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                tabIndex={-1}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
              </button>
            </div>
          </div>

          {/* Strength hint - the same rules the server enforces. */}
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-1.5">
            {PASSWORD_RULES.map((rule) => {
              const ok = rule.test(newPassword);
              return (
                <li
                  key={rule.id}
                  className={`flex items-center gap-1.5 text-[11px] font-semibold ${
                    ok ? 'text-emerald-600' : 'text-slate-400'
                  }`}
                >
                  {ok ? (
                    <Check className="w-3.5 h-3.5 flex-shrink-0" />
                  ) : (
                    <span className="w-3.5 h-3.5 flex-shrink-0 rounded-full border border-slate-300" />
                  )}
                  <span>{rule.label}</span>
                </li>
              );
            })}
          </ul>

          <div>
            <label htmlFor="forgot-confirm-password" className={labelClass}>
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="forgot-confirm-password"
                name="confirm_password"
                type={showPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className={`${inputClass} pr-4`}
              />
            </div>
            {confirmPassword.length > 0 && !passwordMatches && (
              <p className="mt-1.5 text-[11px] font-semibold text-rose-600">
                Passwords do not match.
              </p>
            )}
          </div>

          <button
            id="forgot-save-password-btn"
            type="submit"
            disabled={loading}
            className="w-full h-12 mt-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          >
            {loading ? spinner('Saving…') : <span>Reset Password</span>}
          </button>
        </form>

        <div className="text-center pt-4">
          <button
            type="button"
            onClick={goToLogin}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500 hover:text-slate-700"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Start over</span>
          </button>
        </div>
      </div>
    );
  }

  /* ======================== DONE ========================================= */
  return (
    <div className="w-full text-center">
      <div className="w-12 h-12 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4">
        <CircleCheck className="w-6.5 h-6.5 text-emerald-600" />
      </div>
      <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
        Password Reset
      </h2>
      <p className="text-xs sm:text-sm text-slate-500 mt-2 mb-6 leading-relaxed">
        Your password has been changed and every other session on this account was signed out.
        Sign in with your new password to continue.
      </p>

      <Link
        id="forgot-back-to-login-btn"
        to="/login"
        className="w-full h-12 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 transition-all"
      >
        <span>Sign In to SCHOLARIS</span>
      </Link>
    </div>
  );
};

export default ForgotPassword;
