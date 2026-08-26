import React, { useEffect, useState } from 'react';
import { marksService } from '../../services/marks';
import { examService } from '../../services/exam';
import { Mark } from '../../types';
import { Exam } from '../../types/exam';
import { BarChart2, Download } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const PrincipalMarksPage: React.FC = () => {
  const [marks, setMarks] = useState<Mark[]>([]);
  const [exams, setExams] = useState<Record<number, Exam>>({});
  const [allExams, setAllExams] = useState<Exam[]>([]);
  const [loading, setLoading] = useState(false);
  const [examFilter, setExamFilter] = useState<string>('');

  useEffect(() => {
    setLoading(true);
    Promise.all([
      marksService.listMarks({
        exam_id: examFilter ? Number(examFilter) : undefined,
      }),
      examService.listExams(),
    ])
      .then(([marksData, examsData]) => {
        setMarks(marksData.items);
        setAllExams(examsData.items);
        const examMap: Record<number, Exam> = {};
        examsData.items.forEach(ex => {
          examMap[ex.id] = ex;
        });
        setExams(examMap);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [examFilter]);

  const handleExport = () => {
    console.log('Exporting marks data to CSV/Excel...');
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Marks Monitor</h1>
          <p className="text-xs text-slate-500">Review student marks across all classes</p>
        </div>
        <button
          onClick={handleExport}
          className="h-10 px-4 rounded-xl bg-white border border-slate-200 text-slate-700 text-xs font-semibold flex items-center gap-1.5 hover:bg-slate-50 active:scale-95 transition-all flex-shrink-0"
        >
          <Download className="w-3.5 h-3.5" />
          Export
        </button>
      </div>

      {/* Exam Filter */}
      {allExams.length > 0 && (
        <div className="flex gap-2 overflow-x-auto pb-1 -mx-4 px-4">
          <button
            onClick={() => setExamFilter('')}
            className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 transition-all ${
              examFilter === ''
                ? 'bg-emerald-600 text-white shadow-sm'
                : 'bg-white border border-slate-200 text-slate-600'
            }`}
          >
            All Exams
          </button>
          {allExams.map(ex => (
            <button
              key={ex.id}
              onClick={() => setExamFilter(String(ex.id))}
              className={`h-9 px-4 rounded-full text-xs font-semibold whitespace-nowrap flex-shrink-0 transition-all ${
                examFilter === String(ex.id)
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-white border border-slate-200 text-slate-600'
              }`}
            >
              {ex.name}
            </button>
          ))}
        </div>
      )}

      {/* Marks Cards */}
      {loading ? (
        <LoadingSkeleton type="card" count={4} />
      ) : marks.length === 0 ? (
        <EmptyState
          title="No Marks Recorded"
          description="No marks have been recorded matching the selected criteria."
          icon={<BarChart2 className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {marks.map(mark => {
            const exam = exams[mark.exam_id];
            return (
              <div key={mark.id} className="bg-white rounded-2xl border border-slate-200/80 shadow-xs p-4 space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-sm font-semibold text-slate-900">{exam?.name || `Exam #${mark.exam_id}`}</h3>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 shrink-0">
                    {mark.marks_obtained ?? '—'}{exam?.maximum_marks ? ` / ${exam.maximum_marks}` : ''}
                  </span>
                </div>
                <div className="text-xs text-slate-500">
                  <span>Student ID: {mark.student_id}</span>
                  {mark.grade && <span className="ml-3">Grade: {mark.grade}</span>}
                  {mark.remarks && <p className="mt-1 text-slate-400">{mark.remarks}</p>}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default PrincipalMarksPage;
