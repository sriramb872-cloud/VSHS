// src/pages/principal/Parents.tsx
import React, { useState, useEffect } from 'react';

export const Parents: React.FC = () => {
  const [parents, setParents] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(false);
  }, []);

  return (
    <div className="er-section">
      <div className="er-page-header">
        <h1 className="er-page-title">Parent Management</h1>
      </div>

      {error && <div className="er-alert er-alert-danger">{error}</div>}

      <div className="er-card">
        {loading ? (
          <div className="er-loading-spinner"></div>
        ) : parents.length === 0 ? (
          <div className="er-empty-state">No parents found.</div>
        ) : (
          <div className="er-table-container">
            <table className="er-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Mobile Number</th>
                  <th>Child / Student</th>
                </tr>
              </thead>
              <tbody>
                {parents.map((p) => (
                  <tr key={p.id}>
                    <td>{p.full_name}</td>
                    <td>{p.mobile_number}</td>
                    <td>{p.child_name || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Parents;