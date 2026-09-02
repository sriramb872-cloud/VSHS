// src/pages/student/Marks.tsx
import React, { useEffect, useState } from 'react';
import { marksService } from '../../services/marks';
import { StudentMarksViewItem } from '../../types/marks';
import { Award, CheckCircle2, XCircle } from 'lucide-react';
import { LoadingSkeleton, EmptyState } from '../../components/shared';

export const StudentMarksPage: React.FC = () => {
  const [marksList, setMarksList] = useState<StudentMarksViewItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedExamFilter, setSelectedExamFilter] = useState<string>('');

  useEffect(() => {
    setLoading(true);
    marksService
      .getMyMarks()
      .then(res => {
        setMarksList(res.items);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const uniqueExams = Array.from(new Set(marksList.map(m => m.exam_name)));
  const filteredMarks = selectedExamFilter
    ? marksList.filter(m => m.exam_name === selectedExamFilter)
    : marksList;

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-slate-900">My Exam Results & Marks</h1>
        <p className="text-xs text-slate-500">Official evaluated marks released by your teachers</p>
      </div>

      {/* Filter Tabs */}
      {uniqueExams.length > 1 && (
        <div className="flex gap-2 overflow-x-auto pb-1">
          <button
            onClick={() => setSelectedExamFilter('')}
            className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
              selectedExamFilter === ''
                ? 'bg-blue-600 text-white'
                : 'bg-white border border-slate-200 text-slate-600'
            }`}
          >
            All Exams
          </button>
          {uniqueExams.map(exName => (
            <button
              key={exName}
              onClick={() => setSelectedExamFilter(exName)}
              className={`px-3 py-1.5 rounded-full text-xs font-semibold whitespace-nowrap transition-all ${
                selectedExamFilter === exName
                  ? 'bg-blue-600 text-white'
                  : 'bg-white border border-slate-200 text-slate-600'
              }`}
            >
              {exName}
            </button>
          ))}
        </div>
      )}

      {loading ? (
        <LoadingSkeleton type="card" count={3} />
      ) : filteredMarks.length === 0 ? (
        <EmptyState
          title="No Marks Published"
          description="Your marks will be displayed here once your examination results are officially published."
          icon={<Award className="w-10 h-10 text-slate-300" />}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {filteredMarks.map((item, idx) => (
            <div
              key={`${item.exam_subject_id}-${idx}`}
              className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs flex flex-col justify-between space-y-3"
            >
              <div>
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-base font-bold text-slate-900">{item.subject_name}</h3>
                    <p className="text-xs text-slate-500">{item.exam_name} ({item.exam_type})</p>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      item.is_passed
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                        : 'bg-rose-50 text-rose-700 border border-rose-200'
                    }`}
                  >
                    {item.is_passed ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5" />
                    )}
                    {item.is_passed ? 'PASSED' : 'NEEDS IMPROVEMENT'}
                  </span>
                </div>

                <div className="mt-4 flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-slate-900">
                    {item.marks_obtained}
                  </span>
                  <span className="text-sm font-semibold text-slate-400">
                    / {item.max_marks} marks
                  </span>
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                <span>Passing Mark: {item.passing_marks}</span>
                <span className="font-semibold text-slate-700">
                  {Math.round((item.marks_obtained / (item.max_marks || 100)) * 100)}%
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default StudentMarksPage;
