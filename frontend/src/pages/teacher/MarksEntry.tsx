// src/pages/teacher/MarksEntry.tsx
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Save, CheckCircle2, Lock } from 'lucide-react';
import { examService } from '../../services/exam';
import { marksService } from '../../services/marks';
import { enrollmentsService } from '../../services/enrollments';
import { Exam, ExamSubject } from '../../types/exam';
import { StudentEnrollment } from '../../types';
import { LoadingSkeleton } from '../../components/shared';

interface SummativeRow {
  student_id: number;
  student_name: string;
  roll_number: string;
  marks_obtained: number | '';
  remarks: string;
}

interface FormativeRow {
  student_id: number;
  student_name: string;
  roll_number: string;
  written_test: number | '';
  project: number | '';
  read_reflection: number | '';
  notebook: number | '';
}

// Safely extract a human-readable message from an API error.
// FastAPI validation errors send `detail` as an ARRAY of
// {type, loc, msg, input} objects, not a string — rendering that
// array directly in JSX crashes React ("Objects are not valid as a
// React child"). This normalizes any shape down to a plain string.
const getErrorMessage = (err: any, fallback: string): string => {
  const detail = err?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: any) => (typeof d === 'string' ? d : d?.msg || JSON.stringify(d)))
      .join(', ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || JSON.stringify(detail);
  }
  return fallback;
};

export const TeacherMarksEntryPage: React.FC = () => {
  const { examId, examSubjectId } = useParams<{ examId: string; examSubjectId: string }>();
  const navigate = useNavigate();

  const [exam, setExam] = useState<Exam | null>(null);
  const [examSubject, setExamSubject] = useState<ExamSubject | null>(null);
  const [summativeRows, setSummativeRows] = useState<SummativeRow[]>([]);
  const [formativeRows, setFormativeRows] = useState<FormativeRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const alreadySubmitted = useRef(false);

  const examIdNum = Number(examId);
  const examSubjectIdNum = Number(examSubjectId);
  const hasValidParams =
    !!examId && !!examSubjectId && !Number.isNaN(examIdNum) && !Number.isNaN(examSubjectIdNum);

  const loadData = useCallback(async () => {
    // Guard: don't fire any request until we actually have valid numeric
    // ids from the route. Without this, a route/param mismatch results in
    // Number(undefined) === NaN, which gets baked straight into the API
    // URL as ".../exams/NaN" and the backend correctly 422s it.
    if (!hasValidParams) {
      setFeedback({
        type: 'error',
        text: 'Invalid exam or subject reference. Please go back and try again.',
      });
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setFeedback(null);
      const [examData, subjectsData] = await Promise.all([
        examService.getExamById(examIdNum),
        examService.getExamSubjects(examIdNum),
      ]);
      setExam(examData);

      const es = subjectsData.find(s => s.id === examSubjectIdNum);
      if (!es) {
        setFeedback({ type: 'error', text: 'Subject not found in this exam.' });
        setLoading(false);
        return;
      }
      setExamSubject(es);
      alreadySubmitted.current = es.is_marks_submitted;

      // Load enrolled students using section_id and academic_year_id from the exam
      const enrollments = await enrollmentsService.listEnrollments({
        section_id: examData.section_id,
        academic_year_id: examData.academic_year_id,
        limit: 500,
      });

      const isFormative = (examData.assessment_mode || '').toUpperCase() === 'FORMATIVE';

      if (isFormative) {
        setFormativeRows(
          enrollments.map((en: any) => ({
            student_id: en.student_id,
            student_name: en.student_name || en.full_name || `Student #${en.student_id}`,
            roll_number: en.roll_number || '-',
            written_test: '',
            project: '',
            read_reflection: '',
            notebook: '',
          }))
        );
      } else {
        setSummativeRows(
          enrollments.map((en: any) => ({
            student_id: en.student_id,
            student_name: en.student_name || en.full_name || `Student #${en.student_id}`,
            roll_number: en.roll_number || '-',
            marks_obtained: '',
            remarks: '',
          }))
        );
      }
    } catch (err: any) {
      setFeedback({ type: 'error', text: getErrorMessage(err, 'Failed to load marks entry data.') });
    } finally {
      setLoading(false);
    }
  }, [examIdNum, examSubjectIdNum, hasValidParams]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const isFormative = (exam?.assessment_mode || '').toUpperCase() === 'FORMATIVE';
  const isPublished = (exam?.status || '').toUpperCase() === 'PUBLISHED';
  const isLocked = isPublished || alreadySubmitted.current;

  const handleSummativeChange = (studentId: number, field: 'marks_obtained' | 'remarks', value: string) => {
    setSummativeRows(prev =>
      prev.map(r =>
        r.student_id === studentId
          ? { ...r, [field]: field === 'marks_obtained' ? (value === '' ? '' : Number(value)) : value }
          : r
      )
    );
  };

  const handleFormativeChange = (
    studentId: number,
    field: 'written_test' | 'project' | 'read_reflection' | 'notebook',
    value: string
  ) => {
    setFormativeRows(prev =>
      prev.map(r =>
        r.student_id === studentId
          ? { ...r, [field]: value === '' ? '' : Number(value) }
          : r
      )
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!hasValidParams) return;
    if (isLocked && !window.confirm('Marks already submitted. Re-submitting will overwrite existing marks. Continue?')) return;

    setFeedback(null);
    setSubmitting(true);
    try {
      if (isFormative) {
        await marksService.submitFormativeMarks({
          exam_subject_id: examSubjectIdNum,
          marks: formativeRows.map(r => ({
            student_id: r.student_id,
            written_test: Number(r.written_test) || 0,
            project: Number(r.project) || 0,
            read_reflection: Number(r.read_reflection) || 0,
            notebook: Number(r.notebook) || 0,
          })),
        });
      } else {
        const invalidRow = summativeRows.find(
          r => r.marks_obtained !== '' && Number(r.marks_obtained) > (examSubject?.maximum_marks ?? Infinity)
        );
        if (invalidRow) {
          setFeedback({
            type: 'error',
            text: `Marks for ${invalidRow.student_name} exceed maximum (${examSubject?.maximum_marks}).`,
          });
          return;
        }
        await marksService.submitMarks({
          exam_subject_id: examSubjectIdNum,
          marks: summativeRows
            .filter(r => r.marks_obtained !== '')
            .map(r => ({
              student_id: r.student_id,
              marks_obtained: Number(r.marks_obtained),
              remarks: r.remarks || undefined,
            })),
        });
      }
      alreadySubmitted.current = true;
      setFeedback({ type: 'success', text: 'Marks submitted successfully! Class teacher has been notified.' });
    } catch (err: any) {
      setFeedback({
        type: 'error',
        text: getErrorMessage(err, 'Failed to submit marks.'),
      });
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-6">
        <LoadingSkeleton type="card" count={3} />
      </div>
    );
  }

  if (!exam || !examSubject) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-slate-500">
        {feedback?.text || 'Unable to load marks entry. Please go back and try again.'}
      </div>
    );
  }

  const studentCount = isFormative ? formativeRows.length : summativeRows.length;

  return (
    <form onSubmit={handleSubmit} className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Back */}
      <button
        type="button"
        onClick={() => navigate(`/teacher/exams/${examId}`)}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-4 h-4" /> Back to Exam Details
      </button>

      {/* Header */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-5 shadow-xs space-y-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900">{examSubject.subject_name}</h1>
            <p className="text-xs text-slate-500 mt-0.5">
              {exam.name} · {exam.grade_name || `Grade ${exam.grade_id}`} – {exam.section_name || `Sec ${exam.section_id}`}
            </p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <span className={`px-3 py-1 rounded-full text-xs font-bold ${
              isPublished ? 'bg-emerald-50 text-emerald-700' : alreadySubmitted.current ? 'bg-amber-50 text-amber-700' : 'bg-blue-50 text-blue-700'
            }`}>
              {isPublished ? '🔒 Published' : alreadySubmitted.current ? '✓ Submitted' : 'Pending Entry'}
            </span>
            <span className="text-xs text-slate-400">{exam.assessment_mode}</span>
          </div>
        </div>

        {isFormative ? (
          <div className="flex gap-4 text-xs text-slate-600">
            <span>Written Test: <strong>/20</strong></span>
            <span>Project: <strong>/5</strong></span>
            <span>Read Reflection: <strong>/5</strong></span>
            <span>Notebook: <strong>/5</strong></span>
            <span>Total: <strong>/35</strong></span>
          </div>
        ) : (
          <div className="flex gap-4 text-xs text-slate-600">
            <span>Maximum Marks: <strong>{examSubject.maximum_marks}</strong></span>
            <span>Passing Marks: <strong>{examSubject.passing_marks}</strong></span>
          </div>
        )}
      </div>

      {/* Feedback */}
      {feedback && (
        <div className={`p-4 rounded-xl text-sm font-medium ${
          feedback.type === 'success'
            ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
            : 'bg-rose-50 text-rose-800 border border-rose-200'
        }`}>
          {feedback.text}
        </div>
      )}

      {/* Locked Banner */}
      {isLocked && !feedback && (
        <div className="flex items-center gap-2 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-sm font-medium">
          <Lock className="w-4 h-4 shrink-0" />
          {isPublished
            ? 'Exam results have been published. Marks are read-only.'
            : 'Marks have already been submitted. You can re-submit to update them.'}
        </div>
      )}

      {/* Marks Table */}
      {studentCount === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200/80 p-8 text-center text-sm text-slate-500">
          No students enrolled in this class section.
        </div>
      ) : isFormative ? (
        /* ── FORMATIVE TABLE ── */
        <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Student</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Written<br /><span className="normal-case font-normal">/20</span></th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Project<br /><span className="normal-case font-normal">/5</span></th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Read Refl.<br /><span className="normal-case font-normal">/5</span></th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Notebook<br /><span className="normal-case font-normal">/5</span></th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Total</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {formativeRows.map((row, idx) => {
                  const total =
                    (Number(row.written_test) || 0) +
                    (Number(row.project) || 0) +
                    (Number(row.read_reflection) || 0) +
                    (Number(row.notebook) || 0);
                  return (
                    <tr key={row.student_id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 text-xs text-slate-400">{row.roll_number}</td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-semibold text-slate-800">{row.student_name}</div>
                      </td>
                      {(['written_test', 'project', 'read_reflection', 'notebook'] as const).map(field => {
                        const maxes = { written_test: 20, project: 5, read_reflection: 5, notebook: 5 };
                        return (
                          <td key={field} className="px-2 py-3 text-center">
                            <input
                              type="number"
                              min={0}
                              max={maxes[field]}
                              step={0.5}
                              value={row[field]}
                              onChange={e => handleFormativeChange(row.student_id, field, e.target.value)}
                              disabled={isLocked}
                              className="w-16 text-center border border-slate-200 rounded-lg px-2 py-1.5 text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-slate-50 disabled:text-slate-400"
                              placeholder="0"
                            />
                          </td>
                        );
                      })}
                      <td className="px-4 py-3 text-center">
                        <span className={`text-sm font-bold ${total >= 14 ? 'text-emerald-700' : total > 0 ? 'text-rose-600' : 'text-slate-400'}`}>
                          {total > 0 ? total : '—'}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* ── SUMMATIVE TABLE ── */
        <div className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-slate-50 border-b border-slate-100">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Student</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">
                    Marks<br /><span className="normal-case font-normal">/ {examSubject.maximum_marks}</span>
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">Remarks</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-slate-500 uppercase">Result</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summativeRows.map(row => {
                  const isPassed =
                    row.marks_obtained !== '' && Number(row.marks_obtained) >= examSubject.passing_marks;
                  return (
                    <tr key={row.student_id} className="hover:bg-slate-50/50">
                      <td className="px-4 py-3 text-xs text-slate-400">{row.roll_number}</td>
                      <td className="px-4 py-3">
                        <div className="text-sm font-semibold text-slate-800">{row.student_name}</div>
                      </td>
                      <td className="px-2 py-3 text-center">
                        <input
                          type="number"
                          min={0}
                          max={examSubject.maximum_marks}
                          step={0.5}
                          value={row.marks_obtained}
                          onChange={e => handleSummativeChange(row.student_id, 'marks_obtained', e.target.value)}
                          disabled={isLocked}
                          className="w-20 text-center border border-slate-200 rounded-lg px-2 py-1.5 text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-slate-50 disabled:text-slate-400"
                          placeholder="0"
                        />
                      </td>
                      <td className="px-2 py-3">
                        <input
                          type="text"
                          value={row.remarks}
                          onChange={e => handleSummativeChange(row.student_id, 'remarks', e.target.value)}
                          disabled={isLocked}
                          className="w-full border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-slate-600 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none disabled:bg-slate-50"
                          placeholder="Optional remarks"
                        />
                      </td>
                      <td className="px-4 py-3 text-center">
                        {row.marks_obtained !== '' ? (
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            isPassed ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'
                          }`}>
                            {isPassed ? 'PASS' : 'FAIL'}
                          </span>
                        ) : (
                          <span className="text-slate-300 text-xs">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Submit Button */}
      {!isPublished && (
        <div className="flex justify-end pb-6">
          <button
            type="submit"
            disabled={submitting || studentCount === 0}
            className={`px-8 py-3 rounded-xl text-sm font-bold flex items-center gap-2 shadow-sm transition-all ${
              alreadySubmitted.current
                ? 'bg-amber-600 hover:bg-amber-700 text-white'
                : 'bg-blue-600 hover:bg-blue-700 text-white'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {submitting ? (
              <span>Submitting…</span>
            ) : alreadySubmitted.current ? (
              <>
                <Save className="w-4 h-4" /> Re-submit Marks
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" /> Submit Marks
              </>
            )}
          </button>
        </div>
      )}
    </form>
  );
};

export default TeacherMarksEntryPage;