// src/pages/principal/Homework.tsx
import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, ChevronRight, Calendar, User, GraduationCap, Users, Inbox } from 'lucide-react';
import { EmptyState, LoadingSkeleton } from '../../components/shared';
import { homeworkService } from '../../services/homework';
import { gradesService } from '../../services/grades';
import { sectionsService } from '../../services/sections';
import { timetableService } from '../../services/timetable';
import { Grade, Section } from '../../types';
import { Homework as HomeworkType } from '../../types/homework';
import { WeekdayTabs } from '../../components/shared/WeekdayTabs';
import { useCurrentWeekday } from '../../hooks/useClock';
import { sortByStartTime } from '../../utils/date';

export const Homework: React.FC = () => {
  const [grades, setGrades] = useState<Grade[]>([]);
  const [sections, setSections] = useState<Section[]>([]);
  const [pickerError, setPickerError] = useState<string | null>(null);
  const [pickerLoading, setPickerLoading] = useState<boolean>(true);

  // Class-first: nothing timetable/homework related loads before a class is chosen.
  const [gradeId, setGradeId] = useState<number | ''>('');
  const [sectionId, setSectionId] = useState<number | ''>('');

  // Open on the real current day (and follow a day rollover) until the user picks a tab.
  const todayWeekday = useCurrentWeekday();
  const [pickedDay, setPickedDay] = useState<string | null>(null);
  const selectedDay = pickedDay ?? todayWeekday;

  const [timetable, setTimetable] = useState<any[]>([]);
  const [homeworkList, setHomeworkList] = useState<HomeworkType[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Grade + section choices only - never a default class.
  useEffect(() => {
    Promise.all([gradesService.listGrades(), sectionsService.listSections().catch(() => [] as Section[])])
      .then(([gradeList, sectionList]) => {
        setGrades(gradeList);
        setSections(sectionList);
      })
      .catch(() => setPickerError('Failed to load classes.'))
      .finally(() => setPickerLoading(false));
  }, []);

  const gradeSections = useMemo(
    () => (gradeId ? sections.filter(s => s.grade_id === Number(gradeId)) : []),
    [sections, gradeId]
  );

  const handleGradeChange = (value: string) => {
    setGradeId(value ? Number(value) : '');
    setSectionId('');
    setTimetable([]);
    setHomeworkList([]);
    setError(null);
  };

  const handleSectionChange = (value: string) => {
    setSectionId(value ? Number(value) : '');
    setTimetable([]);
    setHomeworkList([]);
    setError(null);
  };

  const classSelected = gradeId !== '' && sectionId !== '';

  // Load this class's timetable + homework once the class is chosen.
  useEffect(() => {
    if (!classSelected) return;
    let cancelled = false;
    setLoading(true);
    setError(null);
    Promise.all([
      timetableService.listTimetables({ grade_id: Number(gradeId), section_id: Number(sectionId), limit: 200 }),
      homeworkService.listHomework({ grade_id: Number(gradeId), section_id: Number(sectionId), limit: 100 }),
    ])
      .then(([schedule, homework]) => {
        if (cancelled) return;
        setTimetable(schedule.items || []);
        setHomeworkList(homework.items || []);
      })
      .catch(() => { if (!cancelled) setError('Failed to load homework for this class.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [classSelected, gradeId, sectionId]);

  // One row per subject taught to this class on the selected weekday, in time order.
  const subjectRows = useMemo(() => {
    const daySlots = timetable.filter(slot => String(slot.day_of_week).toLowerCase() === selectedDay.toLowerCase());
    const bySubject = new Map<number, { slot: any; homework: HomeworkType[] }>();
    sortByStartTime(daySlots).forEach(slot => {
      const key = slot.subject_id ?? `row-${bySubject.size}`;
      const existing = bySubject.get(key);
      if (existing) {
        existing.homework = [];
        return;
      }
      bySubject.set(key, { slot, homework: [] });
    });
    homeworkList.forEach(hw => {
      const row = bySubject.get(hw.subject_id);
      if (row) row.homework.push(hw);
    });
    bySubject.forEach(row => row.homework.sort((a, b) => String(a.due_date).localeCompare(String(b.due_date))));
    return Array.from(bySubject.values());
  }, [timetable, homeworkList, selectedDay]);

  const selectedGrade = grades.find(g => g.id === Number(gradeId));
  const selectedSection = gradeSections.find(s => s.id === Number(sectionId));
  const classLabel = [selectedGrade?.name, selectedSection?.name].filter(Boolean).join(' - ');

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">Homework Overview</h1>
        <p className="text-xs text-slate-500">Pick a class to see subject-wise homework against its timetable</p>
      </div>

      {/* Class selector: grade + section, no default selection */}
      <div className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs space-y-3">
        <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
          <GraduationCap className="w-4 h-4 text-emerald-600" /> Select Class
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-slate-600 flex items-center gap-1">
              <GraduationCap className="w-3.5 h-3.5" /> Grade
            </label>
            <select
              value={gradeId}
              onChange={e => handleGradeChange(e.target.value)}
              disabled={pickerLoading}
              className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs bg-white"
            >
              <option value="">Select grade</option>
              {grades.map(g => (
                <option key={g.id} value={g.id}>{g.name}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 flex items-center gap-1">
              <Users className="w-3.5 h-3.5" /> Section
            </label>
            <select
              value={sectionId}
              onChange={e => handleSectionChange(e.target.value)}
              disabled={gradeId === '' || gradeSections.length === 0}
              className="w-full mt-1 rounded-lg border border-slate-200 p-2 text-xs bg-white"
            >
              <option value="">
                {gradeId === '' ? 'Select a grade first' : gradeSections.length === 0 ? 'No sections for this grade' : 'Select section'}
              </option>
              {gradeSections.map(s => (
                <option key={s.id} value={s.id}>{s.name}</option>
              ))}
            </select>
          </div>
        </div>
        {pickerError && (
          <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{pickerError}</div>
        )}
      </div>

      {!classSelected ? (
        <EmptyState
          title="Select a Class"
          description="Choose a grade and section to view the homework scheduled for its periods."
          icon={<GraduationCap className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <>
          <WeekdayTabs selectedDay={selectedDay} onChange={setPickedDay} id="principal-homework" />

          {loading ? (
            <LoadingSkeleton type="list" count={4} />
          ) : (
            <>
              <p className="text-xs text-slate-500">
                {classLabel} · {subjectRows.length} period{subjectRows.length === 1 ? '' : 's'} on {selectedDay}
                {subjectRows.length > 0 ? '; homework is matched per subject.' : '.'}
              </p>

              {error && (
                <div className="p-3 bg-rose-50 border border-rose-200 rounded-xl text-rose-700 text-xs">{error}</div>
              )}

              {subjectRows.length === 0 ? (
                <EmptyState
                  title={`No Periods on ${selectedDay}`}
                  description={`${classLabel} has no scheduled periods on ${selectedDay}, so there is no homework to show.`}
                  icon={<Calendar className="w-10 h-10 text-slate-300" />}
                />
              ) : (
                <div className="space-y-2.5">
                  {subjectRows.map(({ slot, homework }) => (
                    <div key={String(slot.subject_id ?? slot.id)} className="bg-white border border-slate-200/80 rounded-2xl p-4 shadow-xs">
                      <div className="flex items-center justify-between gap-3 mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <div className="w-9 h-9 rounded-xl bg-emerald-50 flex items-center justify-center flex-shrink-0">
                            <BookOpen className="w-4 h-4 text-emerald-600" />
                          </div>
                          <div className="min-w-0">
                            <p className="text-sm font-semibold text-slate-900 truncate">{slot.subject_name || 'Subject'}</p>
                            <p className="text-xs text-slate-500">{slot.start_time} - {slot.end_time}</p>
                          </div>
                        </div>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide ${homework.length > 0 ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                          {homework.length > 0 ? `${homework.length} assigned` : 'No homework'}
                        </span>
                      </div>

                      {homework.length === 0 ? (
                        <div className="flex items-center gap-2 rounded-xl bg-slate-50 border border-slate-200/70 px-3 py-2.5">
                          <Inbox className="w-4 h-4 text-slate-400 flex-shrink-0" />
                          <p className="text-xs text-slate-500">No homework assigned for this period on {selectedDay}.</p>
                        </div>
                      ) : (
                        <div className="space-y-2">
                          {homework.map(hw => (
                            <Link
                              key={hw.id}
                              to={`/principal/homework/${hw.id}`}
                              className="flex items-center gap-3 bg-slate-50/70 border border-slate-200/70 rounded-xl p-3 hover:shadow-md active:scale-[0.99] transition-all"
                            >
                              <div className="flex-1 min-w-0">
                                <p className="text-sm font-semibold text-slate-900 truncate">{hw.title}</p>
                                <div className="flex items-center gap-3 mt-1 flex-wrap">
                                  <span className="flex items-center gap-1 text-xs text-slate-500">
                                    <User className="w-3 h-3" /> {hw.teacher_name || 'Teacher'}
                                  </span>
                                  <span className="flex items-center gap-1 text-xs text-slate-500">
                                    <Calendar className="w-3 h-3" /> Due {hw.due_date}
                                  </span>
                                </div>
                              </div>
                              <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
};

export default Homework;
