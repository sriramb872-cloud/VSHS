// src/pages/student/Attendance.tsx
import React, { useState, useEffect } from 'react';

export const StudentAttendance: React.FC = () => {
  const [attendanceData, setAttendanceData] = useState<any | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch student attendance using existing service
    setLoading(false);
  }, []);

  return (
    <div className="er-section">
      <div className="er-page-header">
        <h1 className="er-page-title">My Attendance Record</h1>
      </div>

      {error && <div className="er-alert er-alert-danger">{error}</div>}

      {loading ? (
        <div className="er-loading-spinner"></div>
      ) : !attendanceData ? (
        <div className="er-card">
          <div className="er-empty-state">No attendance records found.</div>
        </div>
      ) : (
        <div className="space-y-6">
          <div className="er-dashboard-grid">
            <div className="er-card">
              <h3 className="er-card-title">Total Working Days</h3>
              <p className="text-2xl font-bold mt-2">{attendanceData.total_days ?? '-'}</p>
            </div>
            <div className="er-card">
              <h3 className="er-card-title">Present Days</h3>
              <p className="text-2xl font-bold mt-2 text-green-600">{attendanceData.present_days ?? '-'}</p>
            </div>
            <div className="er-card">
              <h3 className="er-card-title">Absent Days</h3>
              <p className="text-2xl font-bold mt-2 text-red-600">{attendanceData.absent_days ?? '-'}</p>
            </div>
            <div className="er-card">
              <h3 className="er-card-title">Attendance Percentage</h3>
              <p className="text-2xl font-bold mt-2 text-indigo-600">{attendanceData.percentage ?? '-'}%</p>
            </div>
          </div>

          <div className="er-card">
            <h3 className="er-card-title mb-4">Attendance History</h3>
            {(!attendanceData.records || attendanceData.records.length === 0) ? (
              <div className="er-empty-state">No detailed records available.</div>
            ) : (
              <div className="er-table-container">
                <table className="er-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {attendanceData.records.map((rec: any, idx: number) => (
                      <tr key={idx}>
                        <td>{rec.date}</td>
                        <td>
                          <span className={`er-badge ${rec.status === 'PRESENT' ? 'er-badge-success' : 'er-badge-danger'}`}>
                            {rec.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default StudentAttendance;