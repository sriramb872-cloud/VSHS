// src/components/slipTests/index.tsx
/**
 * Shared presentation for Slip Tests in both portals.
 *
 * Two small components rather than one generic card: the teacher list needs
 * Edit / Cancel actions and the student list needs an expandable detail, and
 * cramming both into one component produced a props matrix nobody could read.
 */
import React, { useState } from 'react';
import {
  CalendarDays,
  Clock,
  User,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Ban,
} from 'lucide-react';
import { StatusBadge } from '../shared/StatusBadge';
import {
  SlipTest,
  SlipTestClassCard,
  formatSlipTestDate,
  formatSlipTestTime,
  slipTestWeekday,
} from '../../types/slipTest';

// ---------------------------------------------------------------------------
// Class card (teacher landing page)
// ---------------------------------------------------------------------------

interface SlipTestClassCardViewProps {
  card: SlipTestClassCard;
  onClick: () => void;
}

/**
 * One "10-A - Mathematics" tile. The whole tile is the tap target (well above
 * the 44px minimum) so it works comfortably at 360px.
 */
export const SlipTestClassCardView: React.FC<SlipTestClassCardViewProps> = ({ card, onClick }) => {
  const hasUpcoming = card.upcoming_count > 0;
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4
                 hover:border-[var(--brand-border)] hover:shadow-md active:scale-[0.99]
                 transition-all min-h-[72px] flex items-center gap-3"
    >
      <div
        className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 ${
          hasUpcoming
            ? 'bg-[var(--brand-light)] text-[var(--brand)]'
            : 'bg-slate-100 text-slate-500'
        }`}
        aria-hidden="true"
      >
        <CalendarDays className="w-5 h-5" />
      </div>

      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-slate-900 truncate">{card.display_name}</p>
        <p className="text-xs text-slate-500 mt-0.5 truncate">
          {[card.grade_name, card.section_name].filter(Boolean).join(' · ') || 'Class'}
        </p>
      </div>

      <div className="text-right flex-shrink-0">
        <span
          className={`inline-flex items-center justify-center min-w-[26px] h-6 px-2 rounded-full text-xs font-bold ${
            hasUpcoming
              ? 'bg-[var(--brand)] text-white'
              : 'bg-slate-100 text-slate-500'
          }`}
        >
          {card.upcoming_count}
        </span>
        <p className="text-[10px] text-slate-400 mt-1 whitespace-nowrap">
          {hasUpcoming ? 'upcoming' : 'none due'}
        </p>
      </div>
    </button>
  );
};

// ---------------------------------------------------------------------------
// Slip test row
// ---------------------------------------------------------------------------

interface SlipTestRowProps {
  slipTest: SlipTest;
  /** Teacher portal: Edit + Cancel on an upcoming, still-scheduled test. */
  onEdit?: () => void;
  onCancel?: () => void;
  cancelling?: boolean;
  /** Student portal: tapping the row expands the description in place. */
  expandable?: boolean;
  /** Student portal: navigates to the detail screen. */
  onOpen?: () => void;
}

export const SlipTestRow: React.FC<SlipTestRowProps> = ({
  slipTest,
  onEdit,
  onCancel,
  cancelling = false,
  expandable = false,
  onOpen,
}) => {
  const [expanded, setExpanded] = useState(false);
  const isCancelled = String(slipTest.status).toLowerCase() === 'cancelled';
  const weekday = slipTestWeekday(slipTest.scheduled_date);
  const timeLabel = formatSlipTestTime(slipTest.start_time);

  // A cancelled test is still shown - students must be able to see that
  // something they were told about is not happening - but never actionable.
  const showActions = !isCancelled && String(slipTest.status).toLowerCase() === 'scheduled'
    && Boolean(onEdit || onCancel);

  const toggle = () => {
    if (expandable) setExpanded((prev) => !prev);
    if (onOpen) onOpen();
  };

  return (
    <div
      className={`bg-white rounded-2xl border shadow-xs overflow-hidden ${
        isCancelled ? 'border-slate-200/80 bg-slate-50/60' : 'border-slate-200/80'
      }`}
    >
      <div
        role={expandable || onOpen ? 'button' : undefined}
        tabIndex={expandable || onOpen ? 0 : undefined}
        onClick={expandable ? toggle : onOpen}
        onKeyDown={
          expandable || onOpen
            ? (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  toggle();
                }
              }
            : undefined
        }
        className={`p-4 ${expandable || onOpen ? 'cursor-pointer hover:bg-slate-50/70 transition-colors' : ''}`}
      >
        <div className="flex items-start gap-3">
          {/* Date block - renders from the string parts, never `new Date()`. */}
          <div
            className={`w-12 h-12 rounded-xl flex flex-col items-center justify-center flex-shrink-0 ${
              isCancelled ? 'bg-slate-200 text-slate-500' : 'bg-[var(--brand-light)] text-[var(--brand-strong)]'
            }`}
          >
            <span className="text-[10px] font-bold uppercase leading-none">
              {formatSlipTestDate(slipTest.scheduled_date).split(' ')[1] ?? ''}
            </span>
            <span className="text-base font-extrabold leading-tight">
              {formatSlipTestDate(slipTest.scheduled_date).split(' ')[0] ?? ''}
            </span>
          </div>

          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-1.5 mb-1">
              <span className="text-[11px] font-bold uppercase tracking-wide text-[var(--brand-strong)] bg-[var(--brand-light)] px-2 py-0.5 rounded-full truncate max-w-[45%]">
                {slipTest.subject_name || `Subject #${slipTest.subject_id}`}
              </span>
              {isCancelled && (
                <StatusBadge status="CANCELLED" label="Cancelled" />
              )}
              {!isCancelled && slipTest.is_past && (
                <StatusBadge status="COMPLETED" label="Past" />
              )}
              {!isCancelled && !slipTest.is_past && (
                <StatusBadge status="SCHEDULED" label="Upcoming" />
              )}
            </div>

            <p
              className={`text-sm font-bold truncate ${isCancelled ? 'text-slate-500 line-through' : 'text-slate-900'}`}
            >
              {slipTest.title}
            </p>

            <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[11px] text-slate-500">
              <span className="inline-flex items-center gap-1">
                <CalendarDays className="w-3 h-3" aria-hidden="true" />
                {formatSlipTestDate(slipTest.scheduled_date)}
                {weekday ? ` (${weekday})` : ''}
              </span>
              {timeLabel && (
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3 h-3" aria-hidden="true" />
                  {timeLabel}
                  {slipTest.duration_minutes ? ` · ${slipTest.duration_minutes} min` : ''}
                </span>
              )}
              <span className="inline-flex items-center gap-1 font-semibold text-slate-700">
                {slipTest.max_marks} marks
              </span>
              {slipTest.teacher_name && (
                <span className="inline-flex items-center gap-1 truncate max-w-full">
                  <User className="w-3 h-3" aria-hidden="true" />
                  <span className="truncate">{slipTest.teacher_name}</span>
                </span>
              )}
            </div>
          </div>

          {expandable && (
            <ChevronUp
              className={`w-4 h-4 text-slate-400 flex-shrink-0 transition-transform mt-1 ${
                expanded ? '' : 'rotate-180'
              }`}
              aria-hidden="true"
            />
          )}
        </div>
      </div>

      {/* Description: always expanded on the teacher side, toggled on the
          student side so the list stays scannable on a 360px screen. */}
      {slipTest.description && (
        <div className={`px-4 ${expandable && !expanded ? 'hidden' : ''}`}>
          <p className="text-xs text-slate-600 leading-relaxed whitespace-pre-line pb-3 border-t border-slate-100 pt-3">
            {slipTest.description}
          </p>
        </div>
      )}

      {slipTest.duplicate_warning && (
        <div className="px-4 pb-3">
          <p className="flex items-start gap-1.5 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-2">
            <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-px" aria-hidden="true" />
            <span>{slipTest.duplicate_warning}</span>
          </p>
        </div>
      )}

      {showActions && (
        <div className="flex items-stretch gap-2 border-t border-slate-100">
          {onEdit && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onEdit();
              }}
              className="flex-1 min-h-[44px] py-2.5 text-xs font-bold text-[var(--brand-strong)]
                         hover:bg-[var(--brand-light)] transition-colors"
            >
              Edit
            </button>
          )}
          {onCancel && (
            <button
              type="button"
              disabled={cancelling}
              onClick={(e) => {
                e.stopPropagation();
                onCancel();
              }}
              className="flex-1 min-h-[44px] py-2.5 text-xs font-bold text-rose-600
                         hover:bg-rose-50 transition-colors flex items-center justify-center gap-1.5
                         disabled:opacity-50"
            >
              <Ban className="w-3.5 h-3.5" aria-hidden="true" />
              {cancelling ? 'Cancelling...' : 'Cancel'}
            </button>
          )}
        </div>
      )}
    </div>
  );
};

export default SlipTestRow;