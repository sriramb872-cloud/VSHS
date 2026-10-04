// src/pages/teacher/SlipTests.tsx
// Page 1 of 2: one card per class + subject the teacher is assigned to.
import React, { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CalendarX2 } from 'lucide-react';
import { slipTestsService } from '../../services/slipTests';
import { SlipTestClassCard } from '../../types/slipTest';
import { SlipTestClassCardView } from '../../components/slipTests';
import { EmptyState, ErrorState, LoadingSkeleton } from '../../components/shared';
import { errorMessage } from '../../helpers/errorMessage';

export const TeacherSlipTestsPage: React.FC = () => {
  const [cards, setCards] = useState<SlipTestClassCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const fetchCards = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await slipTestsService.listMyClasses();
      setCards(data.items || []);
    } catch (err) {
      console.error('Failed to load slip test classes', err);
      setError(errorMessage(err, 'Unable to load your classes. Please try again.'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCards();
  }, [fetchCards]);

  const totalUpcoming = cards.reduce((sum, card) => sum + card.upcoming_count, 0);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Slip Tests</h1>
        <p className="text-xs text-slate-500">
          Pick a class and subject to schedule a short test.
          {cards.length > 0 && (
            <span className="block mt-0.5">
              {totalUpcoming} slip test{totalUpcoming === 1 ? '' : 's'} coming up.
            </span>
          )}
        </p>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : error ? (
        <ErrorState title="Could not load classes" message={error} onRetry={fetchCards} />
      ) : cards.length === 0 ? (
        <EmptyState
          title="No teaching assignments yet"
          description="Slip tests can only be scheduled for a class and subject you teach. Ask your Principal to add you to a timetable or teaching assignment, then reload this page."
          icon={<CalendarX2 className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {cards.map((card) => (
            <SlipTestClassCardView
              key={`${card.grade_id}-${card.section_id}-${card.subject_id}`}
              card={card}
              onClick={() =>
                navigate(
                  `/teacher/slip-tests/class/${card.grade_id}/${card.section_id}/${card.subject_id}`,
                )
              }
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherSlipTestsPage;