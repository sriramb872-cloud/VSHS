// src/pages/student/Homework.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen } from 'lucide-react';
import { homeworkService } from '../../services/homework';
import { Homework } from '../../types/homework';
import { HomeworkCard } from '../../components/homework';
import { LoadingSkeleton, EmptyState, ErrorState } from '../../components/shared';

export const StudentHomeworkPage: React.FC = () => {
  const [homeworkList, setHomeworkList] = useState<Homework[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    setLoading(true);
    setError(null);
    homeworkService
      .listHomework()
      .then(data => setHomeworkList(data.items || []))
      .catch(err => {
        console.error('Failed to load homework', err);
        setError('Unable to load homework. Please try again later.');
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-900">My Homework</h1>
        <p className="text-xs text-slate-500">View assigned tasks and homework</p>
      </div>

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : homeworkList.length === 0 ? (
        <EmptyState
          title="No Homework Assigned"
          description="You currently have no pending homework tasks."
          icon={<BookOpen className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {homeworkList.map(hw => (
            <HomeworkCard
              key={hw.id}
              homework={hw}
              onClick={() => navigate(`/student/homework/${hw.id}`)}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentHomeworkPage;
