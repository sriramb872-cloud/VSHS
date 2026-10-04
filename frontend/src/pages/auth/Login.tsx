// src/pages/auth/Login.tsx
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { Eye, EyeOff, GraduationCap, Loader2, Lock, Phone, ShieldCheck } from 'lucide-react';
import { PASSWORD_RULES, passwordRulesPassed } from '../../utils/passwordRules';

export const Login: React.FC = () => {
  const [mobileNumber, setMobileNumber] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const [forceChange, setForceChange] = useState<boolean>(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [changing, setChanging] = useState<boolean>(false);
  const [pendingRole, setPendingRole] = useState<string | undefined>(undefined);

  const { login, user, mustChangePassword, changePassword } = useAuth();
  const navigate = useNavigate();

  const forceChangeActive = forceChange || mustChangePassword;

  /**
   * Read a human-readable message off an API error.
   *
   * FastAPI sends `detail` as a string, an array (validation) or an object
   * (`{message, code}` - the password endpoints). Rendering any of those raw
   * in JSX crashes React, so everything is flattened to a string here.
   */
  const apiErrorMessage = (err: any, fallback: string): string => {
    const detail = err?.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (detail && typeof detail === 'object' && !Array.isArray(detail)) {
      if (typeof detail.message === 'string' && detail.message) return detail.message;
      if (typeof detail.msg === 'string' && detail.msg) return detail.msg;
    }
    if (Array.isArray(detail)) {
      const msg = detail
        .map((d: any) => (typeof d === 'string' ? d : d?.msg || ''))
        .filter(Boolean)
        .join(', ');
      if (msg) return msg;
    }
    return fallback;
  };

  const goToDashboard = (role?: string) => {
    switch (role) {
      case 'SUPER_ADMIN':
        navigate('/superadmin/dashboard');
        break;
      case 'PRINCIPAL':
        navigate('/principal/dashboard');
        break;
      case 'TEACHER':
        navigate('/teacher/dashboard');
        break;
      case 'STUDENT':
        navigate('/student/dashboard');
        break;
      default:
        navigate('/');
        break;
    }
  };

  const handleForceChange = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (newPassword !== confirmPassword) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (passwordRulesPassed(newPassword) < PASSWORD_RULES.length) {
      setError('Password does not meet the requirements yet.');
      return;
    }

    setChanging(true);
    try {
      await changePassword(currentPassword || password, newPassword);
      setForceChange(false);
      setPassword('');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      goToDashboard(pendingRole || user?.role);
    } catch (err: any) {
      setError(
        apiErrorMessage(
          err,
          'Failed to change password. Please check your current password and try again.'
        )
      );
    } finally {
      setChanging(false);
    }
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const user = await login(mobileNumber, password);

      if (user.must_change_password) {
        setForceChange(true);
        setPendingRole(user.role);
        setCurrentPassword(password);
        return;
      }

      goToDashboard(user.role);
      return;
    } catch (err: any) {
      setError(apiErrorMessage(err, 'Login failed. Please check your credentials and try again.'));
    } finally {
      setLoading(false);
    }
  };

  if (forceChangeActive) {
    return (
      <div className="w-full">
        <div className="text-center mb-6">
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Change Your Password</h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Your password was reset by an administrator. Set a new password to continue.
          </p>
        </div>

        {error && (
          <div className="mb-5 flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs sm:text-sm">
            <span className="font-medium leading-snug">{error}</span>
          </div>
        )}

        <form onSubmit={handleForceChange} className="space-y-4">
          <div>
            <label htmlFor="current-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Current Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="current-password"
                name="current_password"
                type={showCurrentPassword ? 'text' : 'password'}
                required
                autoComplete="current-password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter current password"
                className="w-full h-12 pl-10 pr-11 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              />
              <button
                type="button"
                onClick={() => setShowCurrentPassword((v) => !v)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                tabIndex={-1}
                aria-label={showCurrentPassword ? 'Hide password' : 'Show password'}
              >
                {showCurrentPassword ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
              </button>
            </div>
            {currentPassword === '' && password && (
              <p className="mt-1.5 text-[11px] text-slate-500">
                Use the temporary password you signed in with.
              </p>
            )}
          </div>

          <div>
            <label htmlFor="new-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="new-password"
                name="new_password"
                type={showNewPassword ? 'text' : 'password'}
                required
                minLength={8}
                autoComplete="new-password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="Enter new password"
                className="w-full h-12 pl-10 pr-11 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              />
              <button
                type="button"
                onClick={() => setShowNewPassword((v) => !v)}
                className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
                tabIndex={-1}
                aria-label={showNewPassword ? 'Hide password' : 'Show password'}
              >
                {showNewPassword ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
              </button>
            </div>

            {/* Live checklist of the server's password policy. */}
            <ul className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-x-3 gap-y-1.5">
              {PASSWORD_RULES.map((rule) => {
                const ok = rule.test(newPassword);
                return (
                  <li
                    key={rule.id}
                    className={`flex items-center gap-1.5 text-[11px] font-semibold ${
                      ok ? 'text-emerald-600' : 'text-slate-400'
                    }`}
                  >
                    <span
                      className={`w-3.5 h-3.5 flex-shrink-0 rounded-full border ${
                        ok ? 'bg-emerald-500 border-emerald-500' : 'border-slate-300'
                      }`}
                    />
                    <span>{rule.label}</span>
                  </li>
                );
              })}
            </ul>
          </div>

          <div>
            <label htmlFor="confirm-password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
              Confirm New Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                id="confirm-password"
                name="confirm_password"
                type={showNewPassword ? 'text' : 'password'}
                required
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter new password"
                className="w-full h-12 pl-10 pr-4 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
              />
            </div>
            {confirmPassword.length > 0 && newPassword !== confirmPassword && (
              <p className="mt-1.5 text-[11px] font-semibold text-rose-600">
                Passwords do not match.
              </p>
            )}
          </div>

          <button
            id="change-password-submit-btn"
            type="submit"
            disabled={changing}
            className="w-full h-12 mt-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
          >
            {changing ? (
              <>
                <Loader2 className="w-4.5 h-4.5 animate-spin" />
                <span>Updating…</span>
              </>
            ) : (
              <span>Set New Password</span>
            )}
          </button>
        </form>
      </div>
    );
  }

  return (
    <div className="w-full">
      {/* Header */}
      <div className="text-center mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">Portal Sign In</h2>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">Students use their own mobile number and temporary password. Staff may use their employee ID or mobile.</p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mb-5 flex items-start gap-2.5 p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs sm:text-sm animate-in fade-in duration-150">
          <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z" clipRule="evenodd" />
          </svg>
          <span className="font-medium leading-snug">{error}</span>
        </div>
      )}

      {/* Login Form */}
      <form onSubmit={handleLogin} className="space-y-4">
        {/* Mobile / Student ID / Employee ID */}
        <div>
          <label htmlFor="mobile-number" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
            Login ID
          </label>
          <div className="relative">
            <Phone className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <p className="mb-1.5 text-xs text-slate-500">
              Use your mobile number, email address, student ID, or employee ID.
            </p>
            <input
              id="mobile-number"
              name="mobile_number"
              type="text"
              required
              value={mobileNumber}
              onChange={(e) => setMobileNumber(e.target.value)}
              placeholder="e.g. mobile number, email, SCH2026001, or EMP2026001"
              className="w-full h-12 pl-10 pr-4 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
          </div>
        </div>

        {/* Password */}
        <div>
          <label htmlFor="password" className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
            Password
          </label>
          <div className="relative">
            <Lock className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              id="password"
              name="password"
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              className="w-full h-12 pl-10 pr-11 rounded-xl border border-slate-300/80 bg-slate-50/50 text-slate-900 text-sm placeholder-slate-400 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent transition-all"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition"
              tabIndex={-1}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
            >
              {showPassword ? <EyeOff className="w-4.5 h-4.5" /> : <Eye className="w-4.5 h-4.5" />}
            </button>
          </div>

          {/* Self-service recovery entry point. */}
          <div className="flex justify-end -mt-1">
            <Link
              id="forgot-password-link"
              to="/forgot-password"
              className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
            >
              Forgot password?
            </Link>
          </div>
        </div>

        {/* Submit */}
        <button
          id="login-submit-btn"
          type="submit"
          disabled={loading}
          className="w-full h-12 mt-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm flex items-center justify-center gap-2 shadow-md shadow-indigo-600/20 disabled:opacity-60 disabled:cursor-not-allowed transition-all"
        >
          {loading ? (
            <>
              <Loader2 className="w-4.5 h-4.5 animate-spin" />
              <span>Authenticating…</span>
            </>
          ) : (
            <span>Sign In to SCHOLARIS</span>
          )}
        </button>
      </form>

      {/* Role badges indicator */}
      <div className="mt-6 pt-5 border-t border-slate-100 flex flex-col items-center gap-2">
        <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
          <span>Role-Based Access Control</span>
        </div>
        <div className="flex flex-wrap items-center justify-center gap-1.5 text-[11px] font-semibold">
          <span className="px-2 py-0.5 rounded-md bg-indigo-50 text-indigo-700">Super Admin</span>
          <span className="px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700">Principal</span>
          <span className="px-2 py-0.5 rounded-md bg-blue-50 text-blue-700">Teacher</span>
          <span className="px-2 py-0.5 rounded-md bg-orange-50 text-orange-700">Student</span>
        </div>
      </div>
    </div>
  );
};

export default Login;
