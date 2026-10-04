// src/pages/student/SlipTests.tsx
// Read-only. Upcoming | Past tabs, both derived server-side from the date.
import React, { useCallback, useEffect, useState } from 'react';
import { CalendarX2 } from 'lucide-react';
import { slipTestsService } from '../../services/slipTests';
import { SlipTest, SlipTestTimeFilter } from '../../types/slipTest';
import { SlipTestRow } from '../../components/slipTests';
import { EmptyState, ErrorState, LoadingSkeleton } from '../../components/shared';
import { errorMessage } from '../../helpers/errorMessage';

type Tab = Extract<SlipTestTimeFilter, 'upcoming' | 'past'>;

export const StudentSlipTestsPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>('upcoming');
  const [items, setItems] = useState<SlipTest[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTests = useCallback(async (filter: SlipTestTimeFilter) => {
    setLoading(true);
    setError(null);
    try {
      const data = await slipTestsService.listForStudent(filter);
      setItems(data.items || []);
    } catch (err) {
      console.error('Failed to load slip tests', err);
      setError(errorMessage(err, 'Unable to load your slip tests. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTests(tab);
  }, [tab, fetchTests]);

  // Cancelled tests stay in the list (clearly badged) - a student must be able
  // to see that something they were told about is not happening.
  const cancelledCount = items.filter(
    (item) => String(item.status).toLowerCase() === 'cancelled',
  ).length;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Slip Tests</h1>
        <p className="text-xs text-slate-500">
          Short tests your teacher has scheduled for your class.
          {cancelledCount > 0 && (
            <span className="block mt-0.5 text-amber-700 font-semibold">
              {cancelledCount} of these {cancelledCount === 1 ? 'has' : 'have'} been cancelled.
            </span>
          )}
        </p>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2">
        {(['upcoming', 'past'] as Tab[]).map((value) => (
          <button
            key={value}
            onClick={() => setTab(value)}
            className={`flex-1 sm:flex-none min-h-[40px] px-4 rounded-xl text-xs font-bold capitalize transition-all ${
              tab === value
                ? 'bg-[var(--brand)] text-white shadow-xs'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {value}
          </button>
        ))}
      </div>

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : error ? (
        <ErrorState title="Could not load slip tests" message={error} onRetry={() => fetchTests(tab)} />
      ) : items.length === 0 ? (
        <EmptyState
          title={tab === 'upcoming' ? 'No upcoming slip tests' : 'No past slip tests'}
          description={
            tab === 'upcoming'
              ? 'Nothing has been scheduled yet. Your teacher will notify you when one is.'
              : 'Slip tests appear here automatically once their date has passed.'
          }
          icon={<CalendarX2 className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {items.map((slipTest) => (
            <SlipTestRow key={slipTest.id} slipTest={slipTest} expandable />
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentSlipTestsPage;