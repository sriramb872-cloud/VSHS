// src/pages/student/Settings.tsx
import React, { useEffect, useState } from 'react';
import { settingsService } from '../../services/settings';
import { UserSettingsSection } from '../../components/settings';

export const StudentSettingsPage: React.FC = () => {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    settingsService
      .getUserSettings()
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-12">Loading settings...</div>;
  if (!data) return <div className="text-center py-12 text-red-500">Failed to load settings.</div>;

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">Student Settings</h1>
      <UserSettingsSection
        initialProfile={data.profile_information}
        initialNotifications={data.notification_preferences}
      />
    </div>
  );
};

export default StudentSettingsPage;
/**
 * SCHOLARIS ERP
 *
 * Placeholder Page
 */
