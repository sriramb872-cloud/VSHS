// src/pages/teacher/Announcements.tsx
import React, { useEffect, useState } from 'react';
import { Megaphone } from 'lucide-react';
import { announcementService } from '../../services/announcement';
import { errorMessage } from '../../helpers/errorMessage';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { Announcement } from '../../types';

export const TeacherAnnouncementsPage: React.FC = () => {
  const [items, setItems] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    announcementService
      .listAnnouncements()
      .then((result) => setItems(result.items ?? []))
      .catch((err) => setError(errorMessage(err, 'Failed to load announcements')))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Announcements</h1>
        <p className="text-xs text-slate-500">Notices published by your school</p>
      </div>

      {error && (
        <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
      )}

      {loading ? (
        <LoadingSkeleton type="list" count={3} />
      ) : items.length === 0 ? (
        <EmptyState
          title="No Announcements"
          description="There are no announcements right now."
          icon={<Megaphone className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="space-y-2.5">
          {items.map((item) => (
            <article key={item.id} className="rounded-xl border border-slate-200 bg-white p-4 shadow-xs">
              <h2 className="font-semibold text-slate-900">{item.title}</h2>
              <p className="text-sm text-slate-600 mt-1 whitespace-pre-line">{item.description}</p>
            </article>
          ))}
        </div>
      )}
    </div>
  );
};

export default TeacherAnnouncementsPage;
