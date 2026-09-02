// src/pages/teacher/ExamDetails.tsx
import React, { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Calendar, Award, Layers, CheckCircle2, Clock, Send, AlertTriangle } from 'lucide-react';
import { examService } from '../../services/exam';
import { Exam, ExamSubject, MarksStatusResponse } from '../../types/exam';
import { LoadingSkeleton, ConfirmDialog } from '../../components/shared';

export const TeacherExamDetailsPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [exam, setExam] = useState<Exam | null>(null);
  const [mySubjects, setMySubjects] = useState<ExamSubject[]>([]);
  const [marksStatus, setMarksStatus] = useState<MarksStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);
  const [publishDialogOpen, setPublishDialogOpen] = useState(false);
  const [feedbackMessage, setFeedbackMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const examId = Number(id);

  const loadData = async () => {
    if (!examId) return;
    try {
      setLoading(true);
      const [examData, subjectsData] = await Promise.all([
        examService.getExamById(examId),
        examService.getExamSubjects(examId),
      ]);
      setExam(examData);
      setMySubjects(subjectsData);

      // Try fetching class teacher readiness status if permitted
      try {
        const statusData = await examService.getMarksStatus(examId);
        setMarksStatus(statusData);
      } catch (err) {
        // Not a class teacher or admin for this class, ignore
        setMarksStatus(null);
      }
    } catch (error: any) {
      console.error('Failed to load exam details', error);
      setFeedbackMessage({ type: 'error', text: error.response?.data?.detail || 'Failed to load exam details' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [examId]);

  const handlePublish = async () => {
    try {
      setPublishing(true);
      const res = await examService.publishExam(examId);
      setFeedbackMessage({
        type: 'success',
        text: `${res.message} (${res.students_notified} students notified, ${res.missing_marks_zeroed} missing marks set to 0)`,
      });
      setPublishDialogOpen(false);
      loadData();
    } catch (err: any) {
      setFeedbackMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to publish exam marks' });
    } finally {
      setPublishing(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 max-w-4xl mx-auto px-4 py-6">
        <LoadingSkeleton type="card" count={2} />
      </div>
    );
  }

  if (!exam) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-8 text-center text-slate-500">
        Exam schedule not found.
      </div>
    );
  }

  const isPublished = (exam.status || '').toUpperCase() === 'PUBLISHED';

  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
      {/* Back Button */}
      <button
        onClick={() => navigate('/teacher/exams')}
        className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-600 hover:text-slate-900 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" /> Back to My Exams
      </button>

      {/* Feedback Banner */}
      {feedbackMessage && (
        <div
          className={`p-4 rounded-xl text-sm font-medium flex items-center justify-between ${
            feedbackMessage.type === 'success'
              ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
              : 'bg-rose-50 text-rose-800 border border-rose-200'
          }`}
        >
          <span>{feedbackMessage.text}</span>
          <button onClick={() => setFeedbackMessage(null)} className="text-xs underline ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Exam Header Overview */}
      <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-bold text-slate-900">{exam.name}</h1>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-purple-700">
                {exam.assessment_mode}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">{exam.exam_type}</p>
          </div>

          <div className="flex items-center gap-2">
            <span
              className={`px-3 py-1 rounded-full text-xs font-bold ${
                isPublished
                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                  : exam.status === 'MARKS_IN_PROGRESS'
                  ? 'bg-amber-50 text-amber-700 border border-amber-200'
                  : 'bg-blue-50 text-blue-700 border border-blue-200'
              }`}
            >
              Status: {exam.status}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-6 pt-4 border-t border-slate-100 text-xs">
          <div className="flex items-center gap-2 text-slate-600">
            <Calendar className="w-4 h-4 text-slate-400" />
            <div>
              <span className="text-slate-400 block">Exam Window</span>
              <span className="font-semibold text-slate-800">{exam.start_date} to {exam.end_date}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-slate-600">
            <Layers className="w-4 h-4 text-slate-400" />
            <div>
              <span className="text-slate-400 block">Class</span>
              <span className="font-semibold text-slate-800">{exam.grade_name || `Grade ${exam.grade_id}`} - {exam.section_name || `Sec ${exam.section_id}`}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 text-slate-600">
            <Award className="w-4 h-4 text-slate-400" />
            <div>
              <span className="text-slate-400 block">Total Subjects</span>
              <span className="font-semibold text-slate-800">{exam.exam_subjects?.length || mySubjects.length} subjects</span>
            </div>
          </div>
        </div>
      </div>

      {/* Teacher's Assigned Subjects for Marks Entry */}
      <div className="space-y-3">
        <div>
          <h2 className="text-lg font-bold text-slate-900">Your Subjects</h2>
          <p className="text-xs text-slate-500">Subjects assigned to you for this examination</p>
        </div>

        {mySubjects.length === 0 ? (
          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 text-center text-xs text-slate-500">
            You do not have any subjects assigned for this exam.
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3">
            {mySubjects.map(sub => (
              <div
                key={sub.id}
                className="bg-white rounded-2xl border border-slate-200/80 p-4 shadow-xs flex items-center justify-between gap-4"
              >
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-slate-900">{sub.subject_name}</h3>
                    {sub.subject_code && (
                      <span className="text-xs text-slate-400">({sub.subject_code})</span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 mt-1 text-xs text-slate-500">
                    <span>Max: {sub.maximum_marks}</span>
                    <span>Pass: {sub.passing_marks}</span>
                    {sub.is_marks_submitted ? (
                      <span className="inline-flex items-center gap-1 text-emerald-600 font-semibold">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Marks Submitted
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-amber-600 font-semibold">
                        <Clock className="w-3.5 h-3.5" /> Pending Submission
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <button
                    onClick={() => navigate(`/teacher/exams/${exam.id}/subjects/${sub.id}/marks`)}
                    className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                      isPublished
                        ? 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                        : sub.is_marks_submitted
                        ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                        : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm'
                    }`}
                  >
                    {isPublished ? 'View Marks (Locked)' : sub.is_marks_submitted ? 'Edit Marks' : 'Enter Marks'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Class Teacher Review & Publish Section (If Class Teacher) */}
      {marksStatus && (
        <div className="bg-white rounded-2xl border border-slate-200/80 p-6 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Class Teacher Marks Review</h2>
              <p className="text-xs text-slate-500">
                Track marks submission across all subjects for your class section
              </p>
            </div>

            {!isPublished && (
              <button
                onClick={() => setPublishDialogOpen(true)}
                className={`px-5 py-2.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all shadow-sm ${
                  marksStatus.is_all_submitted
                    ? 'bg-emerald-600 hover:bg-emerald-700 text-white'
                    : 'bg-amber-600 hover:bg-amber-700 text-white'
                }`}
              >
                <Send className="w-3.5 h-3.5" />
                Publish Results
              </button>
            )}
          </div>

          <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50 text-xs">
            <span className="font-semibold text-slate-700">Completion:</span>
            <span className="font-bold text-slate-900">
              {marksStatus.submitted_subjects} / {marksStatus.total_subjects} Subjects Submitted
            </span>
            {!marksStatus.is_all_submitted && !isPublished && (
              <span className="inline-flex items-center gap-1 text-amber-700 ml-auto font-medium">
                <AlertTriangle className="w-3.5 h-3.5" /> Publishing now will zero-fill unsubmitted subjects
              </span>
            )}
          </div>

          {/* Subjects Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-100 text-slate-400 uppercase font-semibold">
                <tr>
                  <th className="py-2.5 px-3">Subject</th>
                  <th className="py-2.5 px-3">Assigned Teacher</th>
                  <th className="py-2.5 px-3">Max Marks</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {marksStatus.items.map(item => (
                  <tr key={item.exam_subject_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-3 font-semibold text-slate-800">{item.subject_name}</td>
                    <td className="py-3 px-3 text-slate-600">{item.teacher_name || 'Unassigned'}</td>
                    <td className="py-3 px-3 text-slate-600">{item.maximum_marks}</td>
                    <td className="py-3 px-3">
                      {item.is_marks_submitted ? (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700">
                          <CheckCircle2 className="w-3 h-3" /> Submitted
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700">
                          <Clock className="w-3 h-3" /> Pending
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-3 text-right">
                      <button
                        onClick={() => navigate(`/teacher/exams/${exam.id}/subjects/${item.exam_subject_id}/marks`)}
                        className="text-blue-600 hover:text-blue-800 font-semibold"
                      >
                        {isPublished ? 'View' : 'Review / Enter'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Publish Confirmation Modal */}
      <ConfirmDialog
        open={publishDialogOpen}
        title="Publish Exam Results?"
        message={
          !marksStatus?.is_all_submitted
            ? 'Warning: Some subjects have not been submitted yet. Publishing now will record 0 marks for all unsubmitted students, lock the exam, and notify all students. Are you sure you want to proceed?'
            : 'Publishing will release results to all students and lock further mark entries. Continue?'
        }
        confirmLabel={publishing ? 'Publishing...' : 'Confirm & Publish'}
        variant={!marksStatus?.is_all_submitted ? 'danger' : 'primary'}
        onConfirm={handlePublish}
        onCancel={() => setPublishDialogOpen(false)}
      />
    </div>
  );
};

export default TeacherExamDetailsPage;