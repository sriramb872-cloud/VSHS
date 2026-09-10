// src/pages/teacher/StudentProfile.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import studentsService from '../../services/students';

export const TeacherStudentProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [student, setStudent] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const studentId = Number(id);
    if (!Number.isFinite(studentId)) {
      setError('Invalid student reference.');
      setLoading(false);
      return;
    }
    studentsService.getStudent(studentId)
      .then((data) => { if (!cancelled) setStudent(data); })
      .catch(() => { if (!cancelled) setError('Unable to load student profile.'); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [id]);

  return (
    <div className="er-section">
      <div className="er-page-header">
        <h1 className="er-page-title">Student Details</h1>
        <button onClick={() => navigate(-1)} className="er-btn er-btn-secondary">
          Back
        </button>
      </div>

      {error && <div className="er-alert er-alert-danger">{error}</div>}

      {loading ? (
        <div className="er-loading-spinner"></div>
      ) : !student ? (
        <div className="er-card">
          <div className="er-empty-state">Student profile not found.</div>
        </div>
      ) : (
        <div className="er-card">
          <div className="space-y-4">
            <div>
              <span className="er-label">Full Name</span>
              <p className="text-lg font-semibold text-gray-900">{student.full_name}</p>
            </div>
            <div>
              <span className="er-label">Mobile Number</span>
              <p className="text-gray-700">{student.mobile_number}</p>
            </div>
            <div>
              <span className="er-label">Admission Number</span>
              <p className="text-gray-700">{student.admission_number || '-'}</p>
            </div>
            <div>
              <span className="er-label">Roll Number</span>
              <p className="text-gray-700">{student.roll_number ?? '-'}</p>
            </div>
            <div>
              <span className="er-label">Grade / Section</span>
              <p className="text-gray-700">
                {student.grade_section || (student.grade_id || student.section_id
                  ? `Grade ${student.grade_id ?? '-'} / Section ${student.section_id ?? '-'}`
                  : '-')}
              </p>
            </div>
            <div>
              <span className="er-label">Parent / Guardian</span>
              <p className="text-gray-700">{student.father_name || student.mother_name || '-'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherStudentProfile;
