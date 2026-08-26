// src/pages/teacher/StudentProfile.tsx
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

export const TeacherStudentProfile: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [student, setStudent] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch student details using route parameter id
    setLoading(false);
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
              <span className="er-label">Grade / Section</span>
              <p className="text-gray-700">{student.grade_section || '-'}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default TeacherStudentProfile;