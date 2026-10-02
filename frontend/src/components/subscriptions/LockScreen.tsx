// src/components/subscriptions/LockScreen.tsx
/**
 * The subscription lock screen.
 *
 * Shown in place of the *content* area only - the sidebar, header, profile and
 * sign-out stay mounted, because an expired subscription is a billing state,
 * not a session state: the user is still signed in and must be able to reach
 * their profile, settings, notifications, the subscription page and logout.
 *
 * Every value rendered here comes from `AccessStatus`, i.e. from the one
 * authoritative resolver on the server. No local countdown, no guessing.
 */
import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Lock, User, Settings, CreditCard, CalendarClock } from 'lucide-react';
import type { AccessStatus } from '../../types/subscription';
import { formatDate, lockBody, lockHeadline, reasonLabel, pluralDays, daysRemaining } from './format';
import { AccessBadge } from './AccessBadge';

/** Where "Renew" sends each role (parent path of the role's own shell). */
const SUBSCRIPTION_PATHS: Record<string, string> = {
  SUPER_ADMIN: '/superadmin/subscriptions',
  PRINCIPAL: '/principal/subscription',
  TEACHER: '/teacher/subscription',
  STUDENT: '/student/subscription',
};

const PROFILE_PATHS: Record<string, string> = {
  PRINCIPAL: '/principal/profile',
  TEACHER: '/teacher/profile',
  STUDENT: '/student/profile',
  SUPER_ADMIN: '/superadmin/profile',
};

const SETTINGS_PATHS: Record<string, string> = {
  PRINCIPAL: '/principal/settings',
  TEACHER: '/teacher/settings',
  STUDENT: '/student/settings',
  SUPER_ADMIN: '/superadmin/settings',
};

interface LockScreenProps {
  status: AccessStatus;
  displayName?: string | null;
}

export const LockScreen: React.FC<LockScreenProps> = ({ status, displayName }) => {
  const navigate = useNavigate();
  const location = useLocation();

  const role = (status.role || '').toUpperCase();
  const renewPath = SUBSCRIPTION_PATHS[role] || SUBSCRIPTION_PATHS.STUDENT;
  const profilePath = PROFILE_PATHS[role];
  const settingsPath = SETTINGS_PATHS[role];

  const days = daysRemaining(status.expires_at);
  const showExpiry = Boolean(status.expires_at) && (status.reason === 'EXPIRED' || (days !== null && days >= 0));
  // A lock does not delete paid time: suspension/cancellation keep the end
  // date, so only an entitlement that is genuinely past due reads as "ended".
  const ended = status.reason === 'EXPIRED' || (days !== null && days < 0);

  // Never "lock" the subscription page onto itself.
  const alreadyThere = location.pathname === renewPath;

  return (
    <div className="flex items-center justify-center py-8 px-1 min-h-[60vh]">
      <div className="w-full max-w-lg">
        <div className="rounded-2xl border border-slate-200 bg-white shadow-sm overflow-hidden">
          <div className="px-5 pt-6 pb-5 text-center bg-gradient-to-b from-amber-50 to-white border-b border-amber-100">
            <div className="mx-auto w-12 h-12 rounded-full bg-amber-100 text-amber-700 flex items-center justify-center mb-3">
              <Lock className="w-6 h-6" />
            </div>
            <h1 className="text-lg font-bold text-slate-900">{lockHeadline(status)}</h1>
            <p className="text-xs text-slate-600 mt-1.5 leading-relaxed">{lockBody(status)}</p>
            <div className="mt-3 flex items-center justify-center gap-2">
              <AccessBadge status={status.status} access={status} />
              <span className="text-[11px] text-slate-500">{reasonLabel(status.reason)}</span>
            </div>
          </div>

          <div className="p-5 space-y-4">
            {showExpiry && status.expires_at && (
              <div className="flex items-start gap-2.5 rounded-xl bg-slate-50 border border-slate-200 p-3">
                <CalendarClock className="w-4 h-4 text-slate-500 mt-0.5 flex-shrink-0" />
                <div className="text-xs text-slate-600">
                  <span className="font-semibold text-slate-800">
                    {ended ? 'Ended ' : 'Paid time runs until '}
                  </span>
                  {formatDate(status.expires_at)}
                  {!ended && days !== null && days > 0 ? ` (${pluralDays(days)} left)` : null}
                </div>
              </div>
            )}

            <div className="rounded-xl bg-indigo-50/60 border border-indigo-100 p-3 text-xs text-indigo-900">
              You are still signed in as{' '}
              <span className="font-semibold">{displayName || 'this account'}</span>. Your profile,
              settings, notifications and this subscription page all keep working - only the
              modules above are waiting for an active plan.
            </div>

            {!alreadyThere && (
              <button
                type="button"
                onClick={() => navigate(renewPath)}
                className="w-full flex items-center justify-center gap-2 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-700 active:scale-98 text-white font-bold text-sm shadow-xs transition-all"
              >
                <CreditCard className="w-4 h-4" />
                <span>View plans</span>
              </button>
            )}

            <div className="flex flex-wrap items-center gap-2">
              {profilePath && (
                <button
                  type="button"
                  onClick={() => navigate(profilePath)}
                  className="flex-1 min-w-[7rem] flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
                >
                  <User className="w-3.5 h-3.5" />
                  <span>Profile</span>
                </button>
              )}
              {settingsPath && (
                <button
                  type="button"
                  onClick={() => navigate(settingsPath)}
                  className="flex-1 min-w-[7rem] flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs transition-all"
                >
                  <Settings className="w-3.5 h-3.5" />
                  <span>Settings</span>
                </button>
              )}
            </div>

            <p className="text-[11px] text-slate-400 text-center leading-relaxed">
              Locked modules: attendance, homework, exams, marks, timetable, report cards and
              calendar. Contact your school administrator if you believe this is a mistake.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LockScreen;
