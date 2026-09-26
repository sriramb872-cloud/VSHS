// src/pages/student/Announcements.tsx
import React, { useEffect, useState } from 'react';
import { announcementService } from '../../services/announcement';
import { Announcement } from '../../types';
export const StudentAnnouncementsPage: React.FC = () => { const [items, setItems] = useState<Announcement[]>([]); useEffect(() => { announcementService.listAnnouncements({ status: 'PUBLISHED' }).then(result => setItems(result.items)); }, []); return <div className="space-y-3"><h1 className="text-xl font-bold text-slate-900">Announcements</h1>{items.map(item => <article key={item.id} className="rounded-xl border border-slate-200 p-4"><h2 className="font-semibold">{item.title}</h2><p className="text-sm text-slate-600">{item.description}</p></article>)}</div>; };

export default StudentAnnouncementsPage;
