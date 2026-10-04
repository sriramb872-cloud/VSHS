// src/pages/student/SlipTestDetails.tsx
// Deep-link target for a slip test notification bell entry.
//
// The API answers 404 for another class's test, another school's test and a
// test from a different academic year, so there is no "not authorised" state to
// design here - only "exists and is yours" or "not found".
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, CalendarDays, Clock, Hash, Layers, User } from 'lucide-react';
import { slipTestsService } from '../../services/slipTests';
import {
  SlipTest,
  formatSlipTestDate,
  formatSlipTestTime,
  slipTestWeekday,
} from '../../types/slipTest';
import { ErrorState, LoadingSkeleton, StatusBadge } from '../../components/shared';
import { errorMessage } from '../../helpers/errorMessage';

export const StudentSlipTestDetailsPage: React.FC = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const slipTestId = Number(id);

  const [slipTest, setSlipTest] = useState<SlipTest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isInteger(slipTestId)) {
      setError('That slip test link is not valid.');
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    slipTestsService
      .getForStudent(slipTestId)
      .then((data) => {
        if (!cancelled) setSlipTest(data);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(
          errorMessage(err, 'This slip test is not available for your class.'),
        );
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slipTestId]);

  if (loading) {
    return <LoadingSkeleton type="card" count={2} />;
  }

  if (error || !slipTest) {
    return (
      <div className="space-y-4">
        <button
          onClick={() => navigate('/student/slip-tests')}
          className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Slip Tests
        </button>
        <ErrorState title="Slip test unavailable" message={error ?? 'Not found.'} />
      </div>
    );
  }

  const isCancelled = String(slipTest.status).toLowerCase() === 'cancelled';
  const timeLabel = formatSlipTestTime(slipTest.start_time);
  const weekday = slipTestWeekday(slipTest.scheduled_date);

  const facts = [
    { icon: CalendarDays, label: 'Date', value: `${formatSlipTestDate(slipTest.scheduled_date)}${weekday ? ` (${weekday})` : ''}` },
    ...(timeLabel
      ? [{ icon: Clock, label: 'Time', value: `${timeLabel}${slipTest.duration_minutes ? ` · ${slipTest.duration_minutes} min` : ''}` }]
      : []),
    { icon: Hash, label: 'Maximum marks', value: String(slipTest.max_marks) },
    { icon: Layers, label: 'Class', value: [slipTest.grade_name, slipTest.section_name].filter(Boolean).join(' - ') || '—' },
    ...(slipTest.teacher_name
      ? [{ icon: User, label: 'Teacher', value: slipTest.teacher_name }]
      : []),
  ];

  return (
    <div className="space-y-4">
      <button
        onClick={() => navigate('/student/slip-tests')}
        className="inline-flex items-center gap-2 text-sm text-slate-600 hover:text-slate-900 min-h-[44px]"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Slip Tests
      </button>

      <div
        className={`bg-white rounded-2xl border shadow-xs overflow-hidden ${
          isCancelled ? 'border-slate-200/80' : 'border-[var(--brand-border)]'
        }`}
      >
        <div className={`p-5 ${isCancelled ? 'bg-slate-50' : 'bg-[var(--brand-light)]/40'}`}>
          <div className="flex flex-wrap items-center gap-2 mb-2">
            <span className="text-[11px] font-bold uppercase tracking-wide text-[var(--brand-strong)] bg-white border border-[var(--brand-border)] px-2 py-0.5 rounded-full">
              {slipTest.subject_name || `Subject #${slipTest.subject_id}`}
            </span>
            {isCancelled ? (
              <StatusBadge status="CANCELLED" label="Cancelled" />
            ) : slipTest.is_past ? (
              <StatusBadge status="COMPLETED" label="Past" />
            ) : (
              <StatusBadge status="SCHEDULED" label="Upcoming" />
            )}
          </div>
          <h1 className={`text-lg font-bold ${isCancelled ? 'text-slate-500' : 'text-slate-900'}`}>
            {slipTest.title}
          </h1>
        </div>

        {isCancelled && (
          <div className="px-5 py-3 bg-amber-50 border-b border-amber-200">
            <p className="text-xs font-semibold text-amber-800">
              This slip test was cancelled and will not take place.
            </p>
          </div>
        )}

        <div className="divide-y divide-slate-100">
          {facts.map(({ icon: Icon, label, value }) => (
            <div key={label} className="flex items-center gap-3 px-5 py-3">
              <div className="w-8 h-8 rounded-lg bg-slate-50 flex items-center justify-center flex-shrink-0">
                <Icon className="w-4 h-4 text-slate-500" aria-hidden="true" />
              </div>
              <div className="min-w-0 flex-1 flex items-baseline justify-between gap-3">
                <span className="text-xs font-semibold text-slate-500">{label}</span>
                <span className="text-sm font-semibold text-slate-900 text-right truncate">{value}</span>
              </div>
            </div>
          ))}
        </div>

        {slipTest.description && (
          <div className="px-5 py-4 border-t border-slate-100">
            <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider mb-1.5">
              Syllabus / topics
            </h2>
            <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line break-words">
              {slipTest.description}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default StudentSlipTestDetailsPage;