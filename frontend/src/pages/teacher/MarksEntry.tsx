// src/pages/teacher/MarksEntry.tsx
import React, { useEffect, useState } from 'react';
import { Save, CheckCircle } from 'lucide-react';
import { examService } from '../../services/exam';
import { marksService } from '../../services/marks';
import { Exam } from '../../types/exam';

export const TeacherMarksEntryPage: React.FC = () => {
  const [exams, setExams] = useState<Exam[]>([]);
  const [selectedExamId, setSelectedExamId] = useState<number | ''>('');
  const [selectedExam, setSelectedExam] = useState<Exam | null>(null);
  const [studentMarks, setStudentMarks] = useState<{ student_id: number; marks_obtained: number }[]>([]);
  const [loading, setLoading] = useState(false);
  const [successMessage, setSuccessMessage] = useState('');

  useEffect(() => {
    examService.listExams().then(data => setExams(data.items)).catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedExamId) {
      const exam = exams.find(e => e.id === selectedExamId) || null;
      setSelectedExam(exam);
      // Mock loading enrolled students for the exam's grade/section context
      // In production, fetch actual students list based on grade_id and section_id
      setStudentMarks([
        { student_id: 101, marks_obtained: 0 },
        { student_id: 102, marks_obtained: 0 },
        { student_id: 103, marks_obtained: 0 },
      ]);
    } else {
      setSelectedExam(null);
      setStudentMarks([]);
    }
  }, [selectedExamId, exams]);

  const handleMarkChange = (studentId: number, value: string) => {
    const numValue = value === '' ? 0 : Number(value);
    setStudentMarks(prev =>
      prev.map(item => (item.student_id === studentId ? { ...item, marks_obtained: numValue } : item))
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedExamId) return;

    try {
      setLoading(true);
      setSuccessMessage('');
      await marksService.saveMarks({
        exam_id: Number(selectedExamId),
        marks: studentMarks,
      });
      setSuccessMessage('Marks successfully saved!');
    } catch (error: any) {
      console.error('Failed to save marks', error);
      alert(error.response?.data?.detail || 'Failed to save marks');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Student Marks Entry</h1>
        <p className="text-sm text-gray-500 mt-1">Select an exam schedule to enter and record offline evaluation marks.</p>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <label className="block text-sm font-medium text-gray-700 mb-2">Select Exam Schedule</label>
        <select
          value={selectedExamId}
          onChange={e => setSelectedExamId(e.target.value ? Number(e.target.value) : '')}
          className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white focus:ring-indigo-500 focus:border-indigo-500"
        >
          <option value="">-- Choose Exam --</option>
          {exams.map(ex => (
            <option key={ex.id} value={ex.id}>
              {ex.name} ({ex.exam_type}) - Grade {ex.grade_id}, Sec {ex.section_id}
            </option>
          ))}
        </select>
      </div>

      {selectedExam && (
        <form onSubmit={handleSubmit} className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4 pb-4 border-b border-gray-100">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">{selectedExam.name}</h2>
              <p className="text-xs text-gray-500">Maximum Marks: {selectedExam.maximum_marks}</p>
            </div>
            {successMessage && (
              <span className="inline-flex items-center gap-1 text-sm text-green-600 font-medium">
                <CheckCircle className="w-4 h-4" /> {successMessage}
              </span>
            )}
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-12 text-xs font-semibold text-gray-500 uppercase tracking-wider px-2">
              <div className="col-span-6">Student ID</div>
              <div className="col-span-6">Marks Obtained</div>
            </div>

            {studentMarks.map(row => (
              <div key={row.student_id} className="grid grid-cols-12 items-center gap-4 p-2 bg-gray-50 rounded-md">
                <div className="col-span-6 font-medium text-gray-800">Student #{row.student_id}</div>
                <div className="col-span-6">
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max={selectedExam.maximum_marks}
                    required
                    value={row.marks_obtained}
                    onChange={e => handleMarkChange(row.student_id, e.target.value)}
                    className="w-full px-3 py-1.5 border border-gray-300 rounded-md bg-white text-sm"
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="inline-flex items-center gap-2 px-6 py-2 bg-indigo-600 text-white rounded-md text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
            >
              <Save className="w-4 h-4" /> {loading ? 'Saving Marks...' : 'Save Marks'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
};

export default TeacherMarksEntryPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
